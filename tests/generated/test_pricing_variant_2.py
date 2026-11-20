# HYPOTHÈSE DE CONTRAT (code source non fourni) : les tests supposent
#   quote(panier: dict[str, int], coupon: str | None = None) -> résultat
# où `résultat` expose les attributs `subtotal`, `discount`, `shipping`, `total`
# (valeurs Decimal). Les erreurs métier sont vérifiées via pytest.raises(Exception, match=...).
# À aligner sur minishop.pricing avant exécution.
#
# Prix déduits de la spec (cohérents avec tous les scénarios) :
#   mug 12.50 | hoodie 44.00 | tshirt 19.90 | sticker 2.45
#   livraison 4.90 si sous-total < 50.00, sinon 0.00
#   remise volume 5 % dès 10 unités (arrondi half-up au centime)
#   WELCOME10 : 10 % du sous-total ; FIXED5 : 5.00 fixes ; FREESHIP : livraison offerte

from decimal import ROUND_HALF_UP, Decimal

import pytest

from minishop.pricing import quote

pytestmark = pytest.mark.generated

D = Decimal


def _calculer(panier, coupon=None):
    """Calcule le panier avec ou sans coupon via l'API de pricing."""
    return quote(panier, coupon)


# ---------------------------------------------------------------------------
# Scénarios de la spécification
# ---------------------------------------------------------------------------


def test_panier_vide():
    """Un panier vide a un total et une livraison nuls."""
    r = _calculer({})
    assert r.total == D("0.00")
    assert r.shipping == D("0.00")


def test_achat_simple_avec_frais_de_livraison():
    """Sous 50 euros, la livraison est facturée 4.90 en plus du sous-total."""
    r = _calculer({"mug": 2})
    assert r.subtotal == D("25.00")
    assert r.shipping == D("4.90")
    assert r.total == D("29.90")


def test_livraison_offerte_a_partir_de_50_euros():
    """Au-delà de 50 euros de sous-total, la livraison est offerte."""
    r = _calculer({"hoodie": 1, "mug": 1})
    assert r.shipping == D("0.00")
    assert r.total == D("56.50")


def test_remise_volume_des_10_unites():
    """Dès 10 unités, une remise volume de 5 % s'applique au sous-total."""
    r = _calculer({"sticker": 10})
    assert r.subtotal == D("23.28")


def test_coupon_de_bienvenue():
    """Le coupon WELCOME10 retire 10 % du sous-total."""
    r = _calculer({"mug": 2}, "WELCOME10")
    assert r.discount == D("2.50")
    assert r.total == D("27.40")


def test_coupon_de_bienvenue_sous_le_seuil():
    """Sous le seuil du coupon WELCOME10 (un seul mug), aucune remise n'est appliquée."""
    r = _calculer({"mug": 1}, "WELCOME10")
    assert r.discount == D("0.00")


def test_coupon_de_livraison_offerte():
    """Le coupon FREESHIP annule les frais de livraison."""
    r = _calculer({"sticker": 1}, "FREESHIP")
    assert r.shipping == D("0.00")
    assert r.total == D("2.45")


def test_coupon_inconnu():
    """Un code coupon non référencé lève une erreur 'Coupon inconnu'."""
    with pytest.raises(Exception, match="Coupon inconnu"):
        _calculer({"mug": 1}, "NOEL2026")


def test_produit_inconnu():
    """Un produit absent du catalogue lève une erreur 'Produit inconnu'."""
    with pytest.raises(Exception, match="Produit inconnu"):
        _calculer({"licorne": 1})


def test_coupon_fixed5_au_dessus_du_seuil():
    """Le coupon FIXED5 retire 5.00 fixes lorsque le sous-total est suffisant."""
    r = _calculer({"tshirt": 2}, "FIXED5")
    assert r.discount == D("5.00")
    assert r.total == D("39.70")


def test_remise_volume_et_welcome10():
    """La remise volume et le coupon WELCOME10 se cumulent sur le sous-total."""
    r = _calculer({"sticker": 10}, "WELCOME10")
    assert r.subtotal == D("23.28")
    assert r.discount == D("2.33")
    assert r.shipping == D("4.90")
    assert r.total == D("25.85")


def test_quantite_egale_a_zero():
    """Une quantité nulle lève une erreur 'Quantité hors limites'."""
    with pytest.raises(Exception, match="Quantité hors limites"):
        _calculer({"mug": 0})


# ---------------------------------------------------------------------------
# Cas limites (non cités par la spécification)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "quantite_mugs, livraison_attendue",
    [
        (3, D("4.90")),  # 37.50 < 50 : livraison facturée
        (4, D("0.00")),  # 50.00 exactement : seuil inclus, livraison offerte
        (5, D("0.00")),  # 62.50 : livraison offerte
    ],
)
def test_limite_seuil_livraison_50_euros_inclus(quantite_mugs, livraison_attendue):
    """Le seuil de livraison gratuite est inclus : exactement 50.00 offre la livraison."""
    r = _calculer({"mug": quantite_mugs})
    assert r.shipping == livraison_attendue


@pytest.mark.parametrize(
    "quantite_stickers, sous_total_attendu",
    [
        (9, D("22.05")),  # 9 x 2.45, sans remise volume
        (10, D("23.28")),  # seuil inclus : remise volume de 5 %
        (11, D("26.95")),  # 11 x 2.45 = 26.95 x 0.95 = 25.6025 -> 25.60 (voir ci-dessous)
    ],
)
def test_limite_seuil_remise_volume_inclus(quantite_stickers, sous_total_attendu):
    """La remise volume démarre exactement à 10 unités, pas à 9."""
    if quantite_stickers == 11:
        # 11 x 2.45 = 26.95 ; remise 5 % -> 25.6025 -> 25.60
        sous_total_attendu = D("25.60")
    r = _calculer({"sticker": quantite_stickers})
    assert r.subtotal == sous_total_attendu


def test_limite_arrondi_remise_volume_half_up():
    """La remise volume est arrondie au centime en mode half-up (23.275 -> 23.28)."""
    brut = D("24.50") * D("0.95")  # 23.275
    attendu = brut.quantize(D("0.01"), rounding=ROUND_HALF_UP)
    r = _calculer({"sticker": 10})
    assert r.subtotal == attendu == D("23.28")


@pytest.mark.parametrize(
    "panier, coupon",
    [
        ({"mug": 2, "sticker": 1}, "WELCOME10"),
        ({"tshirt": 2}, "WELCOME10"),
    ],
)
def test_limite_remise_welcome10_est_proportionnelle(panier, coupon):
    """La remise WELCOME10 est exactement 10 % du sous-total, arrondi au centime."""
    r = _calculer(panier, coupon)
    attendu = (r.subtotal * D("0.10")).quantize(D("0.01"), rounding=ROUND_HALF_UP)
    assert r.discount == attendu


def test_limite_fixed5_ne_depend_pas_de_la_quantite():
    """Le coupon FIXED5 retire toujours 5.00, quelle que soit la quantité."""
    r = _calculer({"tshirt": 4}, "FIXED5")
    assert r.discount == D("5.00")


def test_limite_freeship_sur_panier_deja_livre_gratuitement():
    """FREESHIP ne change rien quand la livraison est déjà offerte."""
    r = _calculer({"hoodie": 1, "mug": 1}, "FREESHIP")
    assert r.shipping == D("0.00")
    assert r.total == D("56.50")


@pytest.mark.parametrize("quantite", [-1, -5])
def test_limite_quantite_negative_refusee(quantite):
    """Une quantité négative est refusée comme une quantité hors limites."""
    with pytest.raises(Exception, match="Quantité hors limites"):
        _calculer({"mug": quantite})


@pytest.mark.parametrize(
    "champ",
    ["subtotal", "discount", "shipping", "total"],
)
def test_limite_montants_sont_des_decimal(champ):
    """Tous les montants retournés sont des Decimal, jamais des float."""
    r = _calculer({"mug": 2}, "WELCOME10")
    assert isinstance(getattr(r, champ), Decimal)


@pytest.mark.parametrize(
    "panier, coupon, total_attendu",
    [
        ({"mug": 2}, None, D("29.90")),
        ({"mug": 2}, "WELCOME10", D("27.40")),
        ({"sticker": 1}, "FREESHIP", D("2.45")),
        ({"tshirt": 2}, "FIXED5", D("39.70")),
    ],
)
def test_limite_total_egale_sous_total_moins_remise_plus_livraison(panier, coupon, total_attendu):
    """Le total vaut sous-total - remise + livraison pour toutes les combinaisons."""
    r = _calculer(panier, coupon)
    assert r.total == r.subtotal - r.discount + r.shipping
    assert r.total == total_attendu
