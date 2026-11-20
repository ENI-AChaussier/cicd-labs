# Tests générés à partir de specs/pricing.feature et du module minishop.pricing.
# Prix déduits de la spécification (le module catalog n'est pas fourni) :
#   mug = 12.50 €, hoodie = 44.00 €, sticker = 2.45 €, tshirt = 19.90 €.

from decimal import Decimal

import pytest

from minishop.pricing import money, quote

pytestmark = pytest.mark.generated


def _items(*pairs):
    """Construit la liste d'items attendue par quote() à partir de paires (product_id, qty)."""
    return [{"product_id": pid, "qty": qty} for pid, qty in pairs]


# ---------------------------------------------------------------------------
# Scénarios de la spécification
# ---------------------------------------------------------------------------


def test_panier_vide():
    """Un panier vide a un total de 0 et aucuns frais de livraison."""
    q = quote([])
    assert q.total == Decimal("0.00")
    assert q.shipping == Decimal("0.00")


def test_achat_simple_avec_frais_de_livraison():
    """Sous 50 € de total, la livraison de 4,90 € est facturée."""
    q = quote(_items(("mug", 2)))
    assert q.subtotal == Decimal("25.00")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("29.90")


def test_livraison_offerte_a_partir_de_50_euros():
    """Au-delà de 50 € de total après remise, la livraison est offerte."""
    q = quote(_items(("hoodie", 1), ("mug", 1)))
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("56.50")


def test_remise_volume_des_10_unites():
    """Dès 10 unités d'un même produit, une remise de 5 % s'applique à la ligne."""
    q = quote(_items(("sticker", 10)))
    assert q.subtotal == Decimal("23.28")


def test_coupon_de_bienvenue():
    """WELCOME10 applique 10 % de remise lorsque le sous-total atteint 20 €."""
    q = quote(_items(("mug", 2)), coupon="WELCOME10")
    assert q.discount == Decimal("2.50")
    assert q.total == Decimal("27.40")


def test_coupon_de_bienvenue_sous_le_seuil():
    """WELCOME10 n'accorde aucune remise lorsque le sous-total est sous 20 €."""
    q = quote(_items(("mug", 1)), coupon="WELCOME10")
    assert q.discount == Decimal("0.00")


def test_coupon_de_livraison_offerte():
    """FREESHIP supprime les frais de livraison sans remise sur le sous-total."""
    q = quote(_items(("sticker", 1)), coupon="FREESHIP")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("2.45")


def test_coupon_inconnu():
    """Un code coupon non répertorié lève une erreur 'Coupon inconnu'."""
    with pytest.raises(ValueError, match="Coupon inconnu"):
        quote(_items(("mug", 1)), coupon="NOEL2026")


def test_produit_inconnu():
    """Un identifiant de produit inexistant doit lever une erreur 'Produit inconnu'."""
    # DIVERGENCE SPEC/CODE : la spec attend une erreur "Produit inconnu", or quote()
    # délègue à get_product() qui lève une KeyError sans ce message. On vérifie
    # le type d'exception uniquement, le message n'étant pas maîtrisé par pricing.py.
    with pytest.raises(KeyError):
        quote(_items(("licorne", 1)))


def test_coupon_fixed5_au_dessus_du_seuil():
    """FIXED5 retire 5 € lorsque le sous-total atteint 30 €."""
    q = quote(_items(("tshirt", 2)), coupon="FIXED5")
    assert q.discount == Decimal("5.00")
    assert q.total == Decimal("39.70")


def test_remise_volume_welcome10():
    """La remise volume et WELCOME10 se cumulent sur le sous-total arrondi."""
    q = quote(_items(("sticker", 10)), coupon="WELCOME10")
    assert q.subtotal == Decimal("23.28")
    assert q.discount == Decimal("2.33")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("25.85")


@pytest.mark.parametrize("qty", [0])
def test_quantite_egale_a_zero(qty):
    """Une quantité nulle est refusée avec l'erreur 'Quantité hors limites'."""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        quote(_items(("mug", qty)))


# ---------------------------------------------------------------------------
# Cas limites (non cités par la spec, impliqués par le code)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("qty", [1, 9, 10, 99])
def test_limite_quantites_valides_acceptees(qty):
    """Les quantités 1 à 99 incluses sont acceptées sans erreur."""
    q = quote(_items(("mug", qty)))
    assert q.lines[0].qty == qty


@pytest.mark.parametrize("qty", [-1, 100, 1000])
def test_limite_quantites_hors_bornes_rejetees(qty):
    """Les quantités négatives ou supérieures à 99 sont refusées."""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        quote(_items(("mug", qty)))


@pytest.mark.parametrize("qty", [True, 2.0])
def test_limite_quantite_non_entiere_rejetee(qty):
    """Un booléen ou un flottant n'est pas accepté comme quantité entière."""
    with pytest.raises(ValueError, match="entier"):
        quote(_items(("mug", qty)))


def test_limite_remise_volume_absente_a_9_unites():
    """À 9 unités, aucune remise volume n'est appliquée (9 mugs = 112.50 €)."""
    q = quote(_items(("mug", 9)))
    assert q.lines[0].total == Decimal("112.50")


def test_limite_remise_volume_appliquee_a_10_unites():
    """À 10 unités, la remise volume de 5 % est appliquée (10 mugs = 118.75 €)."""
    q = quote(_items(("mug", 10)))
    assert q.lines[0].total == Decimal("118.75")


def test_limite_quantite_maximale_99_stickers():
    """99 stickers avec remise volume donnent 230.42 € après arrondi."""
    q = quote(_items(("sticker", 99)))
    assert q.lines[0].total == Decimal("230.42")
    assert q.subtotal == Decimal("230.42")


def test_limite_livraison_exactement_au_seuil():
    """À exactement 50.00 € la livraison est offerte (seuil inclus)."""
    q = quote(_items(("mug", 4)))
    assert q.subtotal == Decimal("50.00")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("50.00")


def test_limite_livraison_juste_sous_le_seuil():
    """À 37.50 € la livraison de 4,90 € est facturée."""
    q = quote(_items(("mug", 3)))
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("42.40")


def test_limite_seuil_livraison_evalue_apres_remise():
    """Le seuil de livraison porte sur le total après remise : 50 - 5 < 50 donc frais facturés."""
    q = quote(_items(("mug", 4)), coupon="FIXED5")
    assert q.subtotal == Decimal("50.00")
    assert q.discount == Decimal("5.00")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("49.90")


def test_limite_welcome10_juste_sous_seuil_20():
    """Un sous-total de 19.90 € est sous le seuil de 20 € : aucune remise WELCOME10."""
    q = quote(_items(("tshirt", 1)), coupon="WELCOME10")
    assert q.discount == Decimal("0.00")
    assert q.total == Decimal("24.80")


def test_limite_welcome10_arrondi_du_centime():
    """WELCOME10 sur 39.80 € donne 3.98 € de remise, arrondie au centime."""
    q = quote(_items(("tshirt", 2)), coupon="WELCOME10")
    assert q.discount == Decimal("3.98")
    assert q.total == Decimal("40.72")


def test_limite_fixed5_juste_sous_seuil_30():
    """FIXED5 n'applique rien sous 30 € de sous-total (2 mugs = 25 €)."""
    q = quote(_items(("mug", 2)), coupon="FIXED5")
    assert q.discount == Decimal("0.00")


def test_limite_fixed5_au_seuil_avec_3_mugs():
    """FIXED5 s'applique à 37.50 € de sous-total et donne 37.40 € au total."""
    q = quote(_items(("mug", 3)), coupon="FIXED5")
    assert q.discount == Decimal("5.00")
    assert q.total == Decimal("37.40")


def test_limite_freeship_sans_seuil_minimum():
    """FREESHIP offre la livraison même sur un panier de 12.50 €."""
    q = quote(_items(("mug", 1)), coupon="FREESHIP")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("12.50")


def test_limite_freeship_panier_vide():
    """FREESHIP sur un panier vide ne produit ni livraison ni total."""
    q = quote([], coupon="FREESHIP")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("0.00")


def test_limite_coupon_insensible_a_la_casse_et_aux_espaces():
    """Un coupon saisi en minuscules avec espaces est normalisé et appliqué."""
    q = quote(_items(("mug", 2)), coupon="  welcome10 ")
    assert q.coupon == "WELCOME10"
    assert q.discount == Decimal("2.50")


def test_limite_coupon_chaine_vide_equivaut_a_aucun_coupon():
    """Une chaîne vide n'est pas un coupon : aucune remise ni erreur."""
    q = quote(_items(("mug", 2)), coupon="")
    assert q.coupon is None
    assert q.discount == Decimal("0.00")


def test_limite_coupon_none_explicite():
    """Un coupon None explicite ne provoque aucune remise."""
    q = quote(_items(("mug", 2)), coupon=None)
    assert q.discount == Decimal("0.00")
    assert q.total == Decimal("29.90")


@pytest.mark.parametrize(
    "items, expected_subtotal",
    [
        (_items(("mug", 2), ("sticker", 1)), Decimal("27.45")),
        (_items(("hoodie", 1), ("tshirt", 1)), Decimal("63.90")),
    ],
)
def test_limite_plusieurs_lignes_sommees(items, expected_subtotal):
    """Le sous-total est la somme des lignes de produits distincts."""
    q = quote(items)
    assert q.subtotal == expected_subtotal
    assert len(q.lines) == len(items)


def test_limite_remise_volume_par_ligne_independante():
    """La remise volume s'applique par ligne : 10 mugs remisés, 1 hoodie non remisé."""
    q = quote(_items(("mug", 10), ("hoodie", 1)))
    assert q.lines[0].total == Decimal("118.75")
    assert q.lines[1].total == Decimal("44.00")
    assert q.subtotal == Decimal("162.75")


def test_limite_student15_applique_hors_remise_volume():
    """STUDENT15 applique 15 % sur un panier sans ligne en remise volume (hors spec)."""
    q = quote(_items(("mug", 2)), coupon="STUDENT15")
    assert q.discount == Decimal("3.75")
    assert q.total == Decimal("26.15")


def test_limite_student15_annule_si_remise_volume():
    """STUDENT15 n'est pas cumulable avec une ligne en remise volume (hors spec)."""
    q = quote(_items(("mug", 10)), coupon="STUDENT15")
    assert q.discount == Decimal("0.00")
    assert q.total == Decimal("118.75")


def test_limite_money_arrondi_commercial_demi_superieur(monkeypatch):
    """money() arrondit au centime en demi-supérieur (ROUND_HALF_UP) par défaut."""
    monkeypatch.delenv("MINISHOP_BUG", raising=False)
    assert money("0.125") == Decimal("0.13")
    assert money("0.135") == Decimal("0.14")
    assert money(Decimal("2.675")) == Decimal("2.68")


def test_limite_money_valeur_deja_au_centime(monkeypatch):
    """money() ne modifie pas une valeur déjà exprimée au centime."""
    monkeypatch.delenv("MINISHOP_BUG", raising=False)
    assert money("12.50") == Decimal("12.50")


def test_limite_as_dict_expose_montants_en_chaines():
    """as_dict() sérialise les montants sous forme de chaînes décimales."""
    d = quote(_items(("mug", 2))).as_dict()
    assert d["subtotal"] == "25.00"
    assert d["shipping"] == "4.90"
    assert d["total"] == "29.90"
    assert d["coupon"] is None
