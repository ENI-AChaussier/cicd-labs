"""Tests unitaires des règles de prix — POINT DE DÉPART (Atelier 1).

Complétez ce fichier : objectif >= 90 % de couverture sur minishop/pricing.py.
"""

from decimal import Decimal

import pytest

from minishop.pricing import coupon_discount, line_total, money, quote

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 1) Arrondi monétaire
# ---------------------------------------------------------------------------
def test_money_arrondi_commercial():
    """0.125 s'arrondit à 0.13 (ROUND_HALF_UP), pas 0.12."""
    assert money("0.125") == Decimal("0.13")


def test_money_arrondi_bug_injecte(monkeypatch):
    """On peut activer le bug injecté pour vérifier le chemin MINISHOP_BUG=rounding."""
    monkeypatch.setenv("MINISHOP_BUG", "rounding")
    assert money("0.125") == Decimal("0.12")


# ---------------------------------------------------------------------------
# 2) Calcul d'une ligne
# ---------------------------------------------------------------------------
def test_line_total_sans_remise():
    """Sans remise volume, le total d'une ligne est simplement prix × quantité."""
    assert line_total(Decimal("12.50"), 2) == Decimal("25.00")


# EXO1-CAS2: TEST UNIQUE, PLUSIEURS CAS:
# Avec pytest.mark.parametrize, on peut tester plusieurs cas de seuil en une seule fonction.
@pytest.mark.parametrize(
    "qty, expected",
    [
        (9, Decimal("90.00")),  # juste en dessous du seuil : pas de remise
        (10, Decimal("95.00")),  # seuil inclus : remise de 5 %
    ],
)
def test_line_total_remise_volume(qty, expected):
    """Remise volume : 5 % à partir de 10 unités (seuil inclus)."""
    assert line_total(Decimal("10.00"), qty) == expected


# ---------------------------------------------------------------------------
# 3) Panier vide
# ---------------------------------------------------------------------------
def test_quote_panier_vide():
    """Un panier vide coûte 0 € : pas de frais de livraison."""
    q = quote([])
    assert q.total == Decimal("0.00")
    assert q.shipping == Decimal("0.00")


# ---------------------------------------------------------------------------
# 4) Quantités invalides
# ---------------------------------------------------------------------------
# EXO2-CAS2: TEST UNIQUE: quantités invalides (0, 100, -1, "2", True) -> ValueError
# (astuce : @pytest.mark.parametrize)
@pytest.mark.parametrize("qty", [0, 100, -1, "2", True])
def test_line_total_quantite_invalide(qty):
    """Quantité invalide -> ValueError."""
    with pytest.raises(ValueError):
        line_total(Decimal("10.00"), qty)


# ---------------------------------------------------------------------------
# 5) Coupons WELCOME10 / FIXED5 / FREESHIP
# ---------------------------------------------------------------------------
# EXO3-CAS1: Logique métier commune pour WELCOME10 et FIXED5 :
# sous-total < seuil -> pas de remise, sous-total >= seuil -> remise
@pytest.mark.parametrize(
    "coupon, subtotal, expected_discount",
    [
        ("WELCOME10", Decimal("19.99"), Decimal("0.00")),  # sous-total < 20 € -> pas de remise
        ("WELCOME10", Decimal("20.00"), Decimal("2.00")),  # sous-total >= 20 € -> remise de 10 %
        ("FIXED5", Decimal("29.99"), Decimal("0.00")),  # sous-total < 30 € -> pas de remise
        ("FIXED5", Decimal("30.00"), Decimal("5.00")),  # sous-total >= 30 € -> remise fixe de 5 €
    ],
)
def test_coupon_discount(coupon, subtotal, expected_discount):
    """Test des coupons WELCOME10 et FIXED5 avec seuils inclus/exclus."""
    assert coupon_discount(subtotal, coupon) == expected_discount


@pytest.mark.parametrize("coupon", ["UNKNOWN", "invalid", "123"])
def test_coupon_inconnu_raises_value_error(coupon):
    """Coupon inconnu -> ValueError."""
    with pytest.raises(ValueError):
        coupon_discount(Decimal("50.00"), coupon)


# Cas de casse / espaces autour du coupon.
@pytest.mark.parametrize(
    "coupon, items, expected_discount",
    [
        ("  welcome10  ", [{"product_id": "mug", "qty": 1}], Decimal("0.00")),  # 12.50 < 20
        ("  welcome10  ", [{"product_id": "mug", "qty": 2}], Decimal("2.50")),  # 25.00 >= 20
    ],
)
def test_coupon_case_insensitive(coupon, items, expected_discount):
    """Coupon insensible à la casse et aux espaces."""
    q = quote(items, coupon=coupon)
    assert q.discount == expected_discount


def test_free_shipping_coupon():
    """Coupon FREESHIP -> livraison gratuite."""
    q = quote([{"product_id": "mug", "qty": 1}], coupon="FREESHIP")
    assert q.shipping == Decimal("0.00")


# ---------------------------------------------------------------------------
# 6) Livraison offerte à partir de 50 € APRÈS remise
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "items, coupon, expected_shipping",
    [
        ([{"product_id": "mug", "qty": 4}], None, Decimal("0.00")),  # 4 × 12.50 = 50.00 -> livraison offerte
        ([{"product_id": "tshirt", "qty": 2}], None, Decimal("4.90")),  # 2 × 19.90 = 39.80 -> frais standard
    ],
)
def test_shipping_threshold(items, coupon, expected_shipping):
    """Livraison gratuite à partir de 50 € après remise, sinon frais standard."""
    q = quote(items, coupon=coupon)
    assert q.shipping == expected_shipping


# ---------------------------------------------------------------------------
# 7) Produit inconnu
# ---------------------------------------------------------------------------
def test_unknown_product_raises_keyerror():
    """Produit inconnu -> KeyError."""
    with pytest.raises(KeyError):
        quote([{"product_id": "inconnu", "qty": 1}])


# ---------------------------------------------------------------------------
# 8) Nouvelle règle métier : STUDENT15
# ---------------------------------------------------------------------------
# TDD :
# 1. Rouge : ces tests doivent d'abord échouer tant que STUDENT15 n'est pas implémenté.
# 2. Vert : ajouter le coupon dans pricing.py.
# 3. Refactor : nettoyer sans casser les tests.
@pytest.mark.parametrize(
    "subtotal, expected",
    [
        (Decimal("10.00"), Decimal("1.50")),  # 10 € * 15 % = 1.50
        (Decimal("20.00"), Decimal("3.00")),  # 20 € * 15 % = 3.00
        (Decimal("1.00"), Decimal("0.15")),  # pas de minimum : coupon appliqué même sur un petit montant
    ],
)
def test_student15_applies_without_minimum(subtotal, expected):
    """STUDENT15 applique 15 % sans seuil minimum."""
    assert coupon_discount(subtotal, "STUDENT15") == expected


def test_student15_applies_when_no_bulk_discount():
    """STUDENT15 s'applique si la ligne n'a pas de remise volume."""
    q = quote([{"product_id": "mug", "qty": 1}], coupon="STUDENT15")
    assert q.discount == Decimal("1.88")  # 12.50 × 15 % = 1.875 -> arrondi 1.88


def test_student15_is_ignored_when_bulk_discount_applies():
    """STUDENT15 est non cumulable avec la remise volume sur une même ligne."""
    q = quote([{"product_id": "mug", "qty": 10}], coupon="STUDENT15")
    assert q.discount == Decimal("0.00")
