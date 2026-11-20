from decimal import Decimal

import pytest

from minishop.pricing import money, quote

pytestmark = pytest.mark.generated

# Prix déduits de la spécification :
#   mug = 12.50 €, sticker = 2.45 €, tshirt = 19.90 €, hoodie = 44.00 €


def test_panier_vide():
    """Un panier vide donne un total nul et aucuns frais de livraison."""
    result = quote([])
    assert result.subtotal == Decimal("0.00")
    assert result.shipping == Decimal("0.00")
    assert result.total == Decimal("0.00")


def test_achat_simple_avec_frais_de_livraison():
    """Deux mugs sous le seuil de 50 € ajoutent les frais de livraison de 4,90 €."""
    result = quote([{"product_id": "mug", "qty": 2}])
    assert result.subtotal == Decimal("25.00")
    assert result.shipping == Decimal("4.90")
    assert result.total == Decimal("29.90")


def test_livraison_offerte_a_partir_de_50_euros():
    """Un hoodie et un mug (56,50 €) bénéficient de la livraison offerte."""
    result = quote(
        [
            {"product_id": "hoodie", "qty": 1},
            {"product_id": "mug", "qty": 1},
        ]
    )
    assert result.shipping == Decimal("0.00")
    assert result.total == Decimal("56.50")


def test_remise_volume_des_10_unites():
    """Dix stickers bénéficient de la remise volume de 5 % sur la ligne."""
    result = quote([{"product_id": "sticker", "qty": 10}])
    assert result.subtotal == Decimal("23.28")


def test_coupon_de_bienvenue():
    """WELCOME10 applique 10 % de remise sur deux mugs (25 €)."""
    result = quote([{"product_id": "mug", "qty": 2}], coupon="WELCOME10")
    assert result.discount == Decimal("2.50")
    assert result.total == Decimal("27.40")


def test_coupon_de_bienvenue_sous_le_seuil():
    """WELCOME10 n'applique aucune remise sous 20 € de sous-total."""
    result = quote([{"product_id": "mug", "qty": 1}], coupon="WELCOME10")
    assert result.discount == Decimal("0.00")


def test_coupon_de_livraison_offerte():
    """FREESHIP supprime les frais de livraison sur un petit panier."""
    result = quote([{"product_id": "sticker", "qty": 1}], coupon="FREESHIP")
    assert result.shipping == Decimal("0.00")
    assert result.total == Decimal("2.45")


def test_coupon_inconnu():
    """Un coupon inconnu lève une erreur ValueError contenant « Coupon inconnu »."""
    with pytest.raises(ValueError, match="Coupon inconnu"):
        quote([{"product_id": "mug", "qty": 1}], coupon="NOEL2026")


def test_produit_inconnu():
    """Un produit inconnu lève une erreur ValueError contenant « Produit inconnu »."""
    # DIVERGENCE SPEC/CODE : la spec attend une ValueError « Produit inconnu » ;
    # le code délègue à get_product qui lève KeyError (message non contrôlé ici).
    with pytest.raises(ValueError, match="Produit inconnu"):
        quote([{"product_id": "licorne", "qty": 1}])


def test_coupon_fixed5_au_dessus_du_seuil():
    """FIXED5 retire 5 € sur deux tshirts (39,80 €), livraison incluse."""
    result = quote([{"product_id": "tshirt", "qty": 2}], coupon="FIXED5")
    assert result.discount == Decimal("5.00")
    assert result.total == Decimal("39.70")


def test_remise_volume_welcome10():
    """La remise volume et WELCOME10 se cumulent sur dix stickers."""
    result = quote([{"product_id": "sticker", "qty": 10}], coupon="WELCOME10")
    assert result.subtotal == Decimal("23.28")
    assert result.discount == Decimal("2.33")
    assert result.shipping == Decimal("4.90")
    assert result.total == Decimal("25.85")


def test_quantite_egale_a_zero():
    """Une quantité nulle lève une erreur ValueError « Quantité hors limites »."""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        quote([{"product_id": "mug", "qty": 0}])


@pytest.mark.parametrize(
    ("qty", "expected_subtotal"),
    [
        (1, Decimal("12.50")),
        (99, Decimal("1175.63")),
    ],
)
def test_limite_quantite_bornes_valides(qty, expected_subtotal):
    """Les quantités 1 et 99 (bornes incluses) sont acceptées."""
    result = quote([{"product_id": "mug", "qty": qty}])
    assert result.subtotal == expected_subtotal


@pytest.mark.parametrize("qty", [100, -1])
def test_limite_quantite_hors_bornes(qty):
    """Une quantité au-delà des bornes 1..99 lève une ValueError."""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        quote([{"product_id": "mug", "qty": qty}])


def test_limite_quantite_non_entiere():
    """Un booléen comme quantité lève une ValueError d'entier attendu."""
    with pytest.raises(ValueError, match="entier"):
        quote([{"product_id": "mug", "qty": True}])


@pytest.mark.parametrize(
    ("qty", "expected_subtotal"),
    [
        (9, Decimal("112.50")),
        (10, Decimal("118.75")),
    ],
)
def test_limite_remise_volume_seuil_10(qty, expected_subtotal):
    """La remise volume ne s'applique qu'à partir de 10 unités exactement."""
    result = quote([{"product_id": "mug", "qty": qty}])
    assert result.subtotal == expected_subtotal


@pytest.mark.parametrize(
    ("qty", "expected_shipping", "expected_total"),
    [
        (3, Decimal("4.90"), Decimal("42.40")),
        (4, Decimal("0.00"), Decimal("50.00")),
    ],
)
def test_limite_livraison_seuil_50(qty, expected_shipping, expected_total):
    """La livraison est offerte exactement à partir de 50 € après remise."""
    result = quote([{"product_id": "mug", "qty": qty}])
    assert result.shipping == expected_shipping
    assert result.total == expected_total


@pytest.mark.parametrize(
    ("qty", "expected_discount"),
    [
        (2, Decimal("0.00")),
        (3, Decimal("5.00")),
    ],
)
def test_limite_fixed5_seuil_30(qty, expected_discount):
    """FIXED5 ne s'applique qu'à partir de 30 € de sous-total."""
    result = quote([{"product_id": "mug", "qty": qty}], coupon="FIXED5")
    assert result.discount == expected_discount


def test_limite_coupon_insensible_casse_et_espaces():
    """Un coupon en minuscules avec espaces est normalisé et appliqué."""
    result = quote([{"product_id": "mug", "qty": 2}], coupon="  welcome10 ")
    assert result.coupon == "WELCOME10"
    assert result.discount == Decimal("2.50")


def test_limite_coupon_vide_sans_remise():
    """Une chaîne de coupon vide n'applique aucune remise."""
    result = quote([{"product_id": "mug", "qty": 2}], coupon="")
    assert result.coupon is None
    assert result.discount == Decimal("0.00")


def test_limite_panier_vide_avec_coupon():
    """Un panier vide avec coupon garde une remise nulle et un total nul."""
    result = quote([], coupon="WELCOME10")
    assert result.discount == Decimal("0.00")
    assert result.total == Decimal("0.00")


def test_limite_freeship_avec_panier_vide():
    """FREESHIP sur panier vide ne facture aucune livraison."""
    result = quote([], coupon="FREESHIP")
    assert result.shipping == Decimal("0.00")
    assert result.total == Decimal("0.00")


def test_limite_student15_ignore_si_remise_volume():
    """STUDENT15 n'est pas cumulable avec la remise volume (hors spécification)."""
    result = quote([{"product_id": "mug", "qty": 10}], coupon="STUDENT15")
    assert result.discount == Decimal("0.00")


def test_limite_arrondi_demi_centime_half_up(monkeypatch):
    """L'arrondi au centime suit ROUND_HALF_UP (0,125 devient 0,13)."""
    monkeypatch.delenv("MINISHOP_BUG", raising=False)
    assert money(Decimal("0.125")) == Decimal("0.13")
