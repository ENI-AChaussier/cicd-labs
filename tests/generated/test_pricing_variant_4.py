from decimal import Decimal

import pytest

from minishop.pricing import money, quote

pytestmark = pytest.mark.generated

D = Decimal


def panier(*lignes):
    """Construit une liste d'items {product_id, qty} pour quote()."""
    return [{"product_id": pid, "qty": qty} for qty, pid in lignes]


# ---------------------------------------------------------------------------
# Scénarios de la spécification
# ---------------------------------------------------------------------------


def test_panier_vide():
    """Un panier vide a un total de 0.00 et aucuns frais de livraison."""
    devis = quote([])
    assert devis.total == D("0.00")
    assert devis.shipping == D("0.00")


def test_achat_simple_avec_frais_de_livraison():
    """Deux mugs (25.00 €) sont sous le seuil : livraison facturée 4.90 €, total 29.90 €."""
    devis = quote(panier((2, "mug")))
    assert devis.subtotal == D("25.00")
    assert devis.shipping == D("4.90")
    assert devis.total == D("29.90")


def test_livraison_offerte_a_partir_de_50_euros():
    """Un hoodie et un mug (56.50 €) dépassent le seuil : livraison offerte."""
    devis = quote(panier((1, "hoodie"), (1, "mug")))
    assert devis.shipping == D("0.00")
    assert devis.total == D("56.50")


def test_remise_volume_des_10_unites():
    """Dix stickers bénéficient de la remise volume de 5 % : sous-total 23.28 €."""
    devis = quote(panier((10, "sticker")))
    assert devis.subtotal == D("23.28")


def test_coupon_de_bienvenue():
    """WELCOME10 applique 10 % sur deux mugs (25.00 €) : remise 2.50 €, total 27.40 €."""
    devis = quote(panier((2, "mug")), coupon="WELCOME10")
    assert devis.discount == D("2.50")
    assert devis.total == D("27.40")


def test_coupon_de_bienvenue_sous_le_seuil():
    """WELCOME10 n'est pas appliqué sous 20 € de sous-total (un mug = 12.50 €)."""
    devis = quote(panier((1, "mug")), coupon="WELCOME10")
    assert devis.discount == D("0.00")


def test_coupon_de_livraison_offerte():
    """FREESHIP offre la livraison sur un sticker seul : total 2.45 €."""
    devis = quote(panier((1, "sticker")), coupon="FREESHIP")
    assert devis.shipping == D("0.00")
    assert devis.total == D("2.45")


def test_coupon_inconnu():
    """Un coupon inconnu lève une erreur 'Coupon inconnu'."""
    with pytest.raises(ValueError, match="Coupon inconnu"):
        quote(panier((1, "mug")), coupon="NOEL2026")


def test_produit_inconnu():
    """Un produit absent du catalogue lève une erreur 'Produit inconnu'."""
    # DIVERGENCE SPEC/CODE : la spec attend une erreur de message 'Produit inconnu',
    # alors que le code délègue à get_product() dont le commentaire indique KeyError
    # (message ne contenant pas 'Produit inconnu'). Le test suit la spec.
    with pytest.raises(Exception, match="Produit inconnu"):
        quote(panier((1, "licorne")))


def test_coupon_fixed5_au_dessus_du_seuil():
    """FIXED5 retire 5.00 € sur deux tshirts (39.80 €) ; total 39.70 € avec livraison facturée."""
    devis = quote(panier((2, "tshirt")), coupon="FIXED5")
    assert devis.discount == D("5.00")
    assert devis.total == D("39.70")


def test_remise_volume_plus_welcome10():
    """Remise volume puis WELCOME10 sur dix stickers : remise 2.33 €, total 25.85 €."""
    devis = quote(panier((10, "sticker")), coupon="WELCOME10")
    assert devis.subtotal == D("23.28")
    assert devis.discount == D("2.33")
    assert devis.shipping == D("4.90")
    assert devis.total == D("25.85")


def test_quantite_egale_a_zero():
    """Une quantité de zéro lève une erreur 'Quantité hors limites'."""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        quote(panier((0, "mug")))


# ---------------------------------------------------------------------------
# Cas limites (non cités dans la spécification)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("qty", [0, -1, 100, 1000])
def test_limite_quantite_hors_bornes_levee(qty):
    """Toute quantité hors de l'intervalle 1..99 lève une ValueError."""
    with pytest.raises(ValueError):
        quote(panier((qty, "mug")))


@pytest.mark.parametrize("qty", [1, 99])
def test_limite_quantite_bornes_incluses_acceptees(qty):
    """Les bornes 1 et 99 sont des quantités valides."""
    devis = quote(panier((qty, "mug")))
    assert devis.lines[0].qty == qty


@pytest.mark.parametrize("qty", [2.0, "2", True])
def test_limite_quantite_non_entiere_levee(qty):
    """Une quantité non entière (float, str, bool) lève une ValueError."""
    with pytest.raises(ValueError):
        quote(panier((qty, "mug")))


def test_limite_seuil_remise_volume_9_unites_sans_remise():
    """Neuf mugs (9 × 12.50 €) ne bénéficient pas de la remise volume : 112.50 €."""
    devis = quote(panier((9, "mug")))
    assert devis.subtotal == D("112.50")


def test_limite_seuil_remise_volume_10_unites_avec_remise():
    """Dix mugs atteignent le seuil de remise volume : 125.00 € × 0.95 = 118.75 €."""
    devis = quote(panier((10, "mug")))
    assert devis.subtotal == D("118.75")


def test_limite_livraison_offerte_exactement_50_euros():
    """Quatre mugs font exactement 50.00 € : le seuil est inclus, livraison offerte."""
    devis = quote(panier((4, "mug")))
    assert devis.subtotal == D("50.00")
    assert devis.shipping == D("0.00")
    assert devis.total == D("50.00")


def test_limite_livraison_facturee_juste_sous_50_euros():
    """Trois mugs (37.50 €) sont sous le seuil : livraison facturée 4.90 €."""
    devis = quote(panier((3, "mug")))
    assert devis.shipping == D("4.90")
    assert devis.total == D("42.40")


def test_limite_welcome10_juste_sous_seuil_20_euros():
    """Un tshirt (19.90 €) est juste sous le seuil de 20 € : pas de remise WELCOME10."""
    devis = quote(panier((1, "tshirt")), coupon="WELCOME10")
    assert devis.discount == D("0.00")


def test_limite_welcome10_au_dessus_seuil_20_euros():
    """Deux tshirts (39.80 €) dépassent le seuil : remise de 10 % = 3.98 €."""
    devis = quote(panier((2, "tshirt")), coupon="WELCOME10")
    assert devis.discount == D("3.98")


def test_limite_fixed5_juste_sous_seuil_30_euros():
    """Un tshirt (19.90 €) est sous le seuil de 30 € : pas de remise FIXED5."""
    devis = quote(panier((1, "tshirt")), coupon="FIXED5")
    assert devis.discount == D("0.00")


def test_limite_coupon_insensible_a_la_casse_et_aux_espaces():
    """Le code coupon est normalisé (espaces et casse) et appliqué normalement."""
    devis = quote(panier((2, "mug")), coupon="  welcome10 ")
    assert devis.coupon == "WELCOME10"
    assert devis.discount == D("2.50")


def test_limite_coupon_vide_sans_effet():
    """Un coupon chaîne vide n'entraîne aucune remise."""
    devis = quote(panier((2, "mug")), coupon="")
    assert devis.discount == D("0.00")
    assert devis.total == D("29.90")


def test_limite_freeship_offre_livraison_sous_seuil():
    """FREESHIP supprime les frais même sous le seuil de 50 € (un mug seul)."""
    devis = quote(panier((1, "mug")), coupon="FREESHIP")
    assert devis.shipping == D("0.00")


def test_limite_panier_vide_avec_coupon_valide():
    """Un panier vide avec coupon valide reste à 0.00 partout."""
    devis = quote([], coupon="WELCOME10")
    assert devis.discount == D("0.00")
    assert devis.shipping == D("0.00")
    assert devis.total == D("0.00")


def test_limite_student15_sans_ligne_volume_applique_15_pourcent(monkeypatch):
    """STUDENT15 applique 15 % sur un mug seul (12.50 € → 1.88 € arrondi commercial)."""
    monkeypatch.delenv("MINISHOP_BUG", raising=False)
    devis = quote(panier((1, "mug")), coupon="STUDENT15")
    assert devis.discount == D("1.88")


def test_limite_student15_ignore_si_remise_volume(monkeypatch):
    """STUDENT15 n'est pas appliqué si le panier contient une ligne en remise volume."""
    monkeypatch.delenv("MINISHOP_BUG", raising=False)
    devis = quote(panier((10, "sticker")), coupon="STUDENT15")
    assert devis.discount == D("0.00")


@pytest.mark.parametrize(
    "valeur, attendu",
    [
        ("0.125", "0.13"),
        ("2.345", "2.35"),
        ("2.344", "2.34"),
        ("23.285", "23.29"),
        ("0.004", "0.00"),
    ],
)
def test_limite_arrondi_commercial_half_up(monkeypatch, valeur, attendu):
    """money() arrondit au centime en ROUND_HALF_UP (le 5 final monte)."""
    monkeypatch.delenv("MINISHOP_BUG", raising=False)
    assert money(valeur) == D(attendu)


def test_limite_total_est_somme_sous_total_remise_livraison(monkeypatch):
    """Le total égale sous-total − remise + livraison pour un panier combiné."""
    monkeypatch.delenv("MINISHOP_BUG", raising=False)
    devis = quote(panier((10, "sticker"), (1, "mug")), coupon="WELCOME10")
    assert devis.total == money(devis.subtotal - devis.discount + devis.shipping)


def test_limite_arrondi_remise_volume_sur_99_unites(monkeypatch):
    """99 mugs : 1237.50 € × 0.95 = 1175.625 € arrondi en 1175.63 € (ROUND_HALF_UP)."""
    monkeypatch.delenv("MINISHOP_BUG", raising=False)
    devis = quote(panier((99, "mug")))
    assert devis.subtotal == D("1175.63")


def test_limite_as_dict_montants_en_chaine_decimale():
    """as_dict() expose les montants sous forme de chaînes décimales à deux chiffres."""
    devis = quote(panier((2, "mug")))
    d = devis.as_dict()
    assert d["subtotal"] == "25.00"
    assert d["shipping"] == "4.90"
    assert d["total"] == "29.90"
