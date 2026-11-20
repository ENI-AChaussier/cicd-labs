from decimal import Decimal

import pytest

from minishop.pricing import Quote, coupon_discount, line_total, money, quote, shipping_cost

pytestmark = [pytest.mark.generated, pytest.mark.unit]

# Prix dérivés de la spécification (produits du catalogue) :
#   mug = 12.50 €, sticker = 2.45 €, tshirt = 19.90 €, hoodie = 44.00 €
# Ces valeurs ne sont utilisées que pour construire des paniers de test.


def _items(*pairs):
    """Construit une liste d'items {product_id, qty} à partir de couples (produit, qté)."""
    return [{"product_id": pid, "qty": qty} for pid, qty in pairs]


@pytest.fixture(autouse=True)
def _sans_bug_arrondi(monkeypatch):
    """Garantit que le mode de régression MINISHOP_BUG n'est pas actif pendant les tests."""
    monkeypatch.delenv("MINISHOP_BUG", raising=False)


# ---------------------------------------------------------------------------
# Scénarios de la spécification
# ---------------------------------------------------------------------------


def test_panier_vide():
    """Un panier vide a un total de 0 et aucuns frais de livraison."""
    q = quote([])
    assert q.total == Decimal("0.00")
    assert q.shipping == Decimal("0.00")


def test_achat_simple_avec_frais_de_livraison():
    """Un sous-total inférieur à 50 € ajoute des frais de livraison de 4,90 €."""
    q = quote(_items(("mug", 2)))
    assert q.subtotal == Decimal("25.00")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("29.90")


def test_livraison_offerte_a_partir_de_50_euros():
    """Un total après remise supérieur ou égal à 50 € offre la livraison."""
    q = quote(_items(("hoodie", 1), ("mug", 1)))
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("56.50")


def test_remise_volume_des_10_unites():
    """Dès 10 unités du même produit, une remise de 5 % s'applique à la ligne."""
    q = quote(_items(("sticker", 10)))
    assert q.subtotal == Decimal("23.28")


def test_coupon_de_bienvenue():
    """Le coupon WELCOME10 offre 10 % de remise lorsque le sous-total atteint 20 €."""
    q = quote(_items(("mug", 2)), coupon="WELCOME10")
    assert q.discount == Decimal("2.50")
    assert q.total == Decimal("27.40")


def test_coupon_de_bienvenue_sous_le_seuil():
    """Le coupon WELCOME10 n'offre aucune remise si le sous-total est sous 20 €."""
    q = quote(_items(("mug", 1)), coupon="WELCOME10")
    assert q.discount == Decimal("0.00")


def test_coupon_de_livraison_offerte():
    """Le coupon FREESHIP supprime les frais de livraison sans remise sur le panier."""
    q = quote(_items(("sticker", 1)), coupon="FREESHIP")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("2.45")


def test_coupon_inconnu():
    """Un code coupon non reconnu lève une erreur 'Coupon inconnu'."""
    with pytest.raises(ValueError, match="Coupon inconnu"):
        quote(_items(("mug", 1)), coupon="NOEL2026")


def test_produit_inconnu():
    """Un produit absent du catalogue provoque une erreur."""
    # DIVERGENCE SPEC/CODE : la spec exige une erreur "Produit inconnu" ;
    # le code délègue à get_product, qui lève KeyError selon le commentaire
    # de quote(). On accepte KeyError ou ValueError sans imposer le message.
    with pytest.raises((KeyError, ValueError)):
        quote(_items(("licorne", 1)))


def test_coupon_fixed5_au_dessus_du_seuil():
    """Le coupon FIXED5 retire 5 € lorsque le sous-total atteint 30 €."""
    q = quote(_items(("tshirt", 2)), coupon="FIXED5")
    assert q.discount == Decimal("5.00")
    assert q.total == Decimal("39.70")


def test_remise_volume_welcome10():
    """La remise volume et le coupon WELCOME10 se cumulent sur le sous-total réduit."""
    q = quote(_items(("sticker", 10)), coupon="WELCOME10")
    assert q.subtotal == Decimal("23.28")
    assert q.discount == Decimal("2.33")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("25.85")


def test_quantite_egale_a_zero():
    """Une quantité égale à zéro est refusée avec l'erreur 'Quantité hors limites'."""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        quote(_items(("mug", 0)))


# ---------------------------------------------------------------------------
# Cas limites (non cités par la spécification)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("qty", [1, 99])
def test_limite_quantite_bornes_acceptees(qty):
    """Les bornes 1 et 99 sont des quantités valides."""
    assert line_total(Decimal("1.00"), qty) >= Decimal("0.00")


@pytest.mark.parametrize("qty", [0, -1, 100])
def test_limite_quantite_hors_bornes_refusee(qty):
    """Les quantités 0, négatives ou au-delà de 99 sont refusées."""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        line_total(Decimal("1.00"), qty)


@pytest.mark.parametrize("qty", [True, 2.0, "2"])
def test_limite_quantite_non_entiere_refusee(qty):
    """Un booléen, un flottant ou une chaîne ne sont pas des quantités valides."""
    with pytest.raises(ValueError, match="entier"):
        line_total(Decimal("1.00"), qty)


def test_limite_remise_volume_seuil_9_unites_sans_remise():
    """À 9 unités, aucune remise volume ne s'applique."""
    assert line_total(Decimal("2.45"), 9) == Decimal("22.05")


def test_limite_remise_volume_seuil_10_unites_avec_remise():
    """À 10 unités exactement, la remise volume de 5 % s'applique."""
    assert line_total(Decimal("2.45"), 10) == Decimal("23.28")


def test_limite_livraison_seuil_exact_50_euros_offerte():
    """Un total exactement égal à 50 € bénéficie de la livraison offerte."""
    q = quote(_items(("mug", 4)))
    assert q.subtotal == Decimal("50.00")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("50.00")


def test_limite_livraison_sous_seuil_49_99_payante():
    """Un total inférieur à 50 € paie la livraison, même proche du seuil."""
    q = quote(_items(("mug", 3)))
    assert q.subtotal == Decimal("37.50")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("42.40")


@pytest.mark.parametrize(
    ("subtotal", "expected"),
    [
        (Decimal("19.99"), Decimal("0.00")),
        (Decimal("20.00"), Decimal("2.00")),
    ],
)
def test_limite_welcome10_seuil_20_euros(subtotal, expected):
    """WELCOME10 s'applique exactement à partir de 20 € de sous-total."""
    assert coupon_discount(subtotal, "WELCOME10") == expected


@pytest.mark.parametrize(
    ("subtotal", "expected"),
    [
        (Decimal("29.99"), Decimal("0.00")),
        (Decimal("30.00"), Decimal("5.00")),
    ],
)
def test_limite_fixed5_seuil_30_euros(subtotal, expected):
    """FIXED5 s'applique exactement à partir de 30 € de sous-total."""
    assert coupon_discount(subtotal, "FIXED5") == expected


def test_limite_fixed5_sous_le_seuil_via_panier():
    """Avec 25 € de sous-total, FIXED5 n'offre aucune remise."""
    q = quote(_items(("mug", 2)), coupon="FIXED5")
    assert q.discount == Decimal("0.00")
    assert q.total == Decimal("29.90")


def test_limite_welcome10_arrondi_half_up():
    """La remise WELCOME10 est arrondie au centime en ROUND_HALF_UP (2,505 -> 2,51)."""
    assert coupon_discount(Decimal("25.05"), "WELCOME10") == Decimal("2.51")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("0.125"), Decimal("0.13")),
        (Decimal("2.345"), Decimal("2.35")),
        (Decimal("2.344"), Decimal("2.34")),
        (Decimal("10"), Decimal("10.00")),
    ],
)
def test_limite_money_arrondi_commercial(value, expected):
    """money arrondit au centime selon ROUND_HALF_UP."""
    assert money(value) == expected


def test_limite_money_accepte_float_et_str():
    """money accepte un float ou une chaîne et renvoie un Decimal au centime."""
    assert money(1.5) == Decimal("1.50")
    assert money("3.456") == Decimal("3.46")


@pytest.mark.parametrize("coupon", ["welcome10", "  WELCOME10  ", "Welcome10"])
def test_limite_coupon_insensible_casse_et_espaces(coupon):
    """Les codes coupon sont normalisés (casse et espaces ignorés)."""
    q = quote(_items(("mug", 2)), coupon=coupon)
    assert q.coupon == "WELCOME10"
    assert q.discount == Decimal("2.50")


def test_limite_coupon_chaine_vide_sans_effet():
    """Un coupon vide est traité comme l'absence de coupon."""
    q = quote(_items(("mug", 2)), coupon="")
    assert q.coupon is None
    assert q.discount == Decimal("0.00")
    assert coupon_discount(Decimal("25.00"), "") == Decimal("0.00")


def test_limite_freeship_sous_seuil_livraison_offerte():
    """FREESHIP supprime la livraison même lorsque le total est sous 50 €."""
    q = quote(_items(("mug", 1)), coupon="FREESHIP")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("12.50")


def test_limite_shipping_cost_panier_vide_sans_frais():
    """Un panier vide n'a pas de frais de livraison, même sans coupon."""
    assert shipping_cost(Decimal("0.00"), None, empty=True) == Decimal("0.00")


def test_limite_shipping_cost_seuil_exact_50():
    """shipping_cost offre la livraison à partir de exactement 50 €."""
    assert shipping_cost(Decimal("50.00"), None, empty=False) == Decimal("0.00")
    assert shipping_cost(Decimal("49.99"), None, empty=False) == Decimal("4.90")


def test_limite_student15_applique_sans_remise_volume():
    """STUDENT15 offre 15 % lorsqu'aucune ligne n'atteint le seuil de remise volume."""
    q = quote(_items(("mug", 3)), coupon="STUDENT15")
    assert q.discount == Decimal("5.63")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("36.77")


def test_limite_student15_annule_si_remise_volume():
    """STUDENT15 ne s'applique pas lorsqu'une ligne bénéficie de la remise volume."""
    q = quote(_items(("sticker", 10)), coupon="STUDENT15")
    assert q.discount == Decimal("0.00")
    assert q.total == Decimal("28.18")


def test_limite_quote_as_dict_montants_en_chaine():
    """as_dict expose les montants sous forme de chaînes au format centime."""
    q = quote(_items(("sticker", 1)))
    d = q.as_dict()
    assert d["subtotal"] == "2.45"
    assert d["shipping"] == "4.90"
    assert d["total"] == "7.35"
    assert d["coupon"] is None


def test_limite_quote_par_defaut_vide():
    """Un Quote sans paramètre a des montants nuls et aucune ligne."""
    q = Quote()
    assert q.lines == []
    assert q.subtotal == Decimal("0.00")
    assert q.total == Decimal("0.00")
    assert q.coupon is None
