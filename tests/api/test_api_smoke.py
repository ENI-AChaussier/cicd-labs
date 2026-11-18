"""Tests d'API — POINT DE DÉPART (Atelier 1, puis Atelier 9)."""

import pytest

pytestmark = pytest.mark.api


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_liste_produits(client):
    r = client.get("/products")
    assert r.status_code == 200
    assert {"mug", "tshirt"} <= {p["id"] for p in r.json()}


def test_produit_par_id(client):
    r = client.get("/products/mug")
    assert r.status_code == 200
    assert r.json()["id"] == "mug"
    assert r.json()["price"] == "12.50"


def test_produit_inconnu(client):
    r = client.get("/products/inconnu")
    assert r.status_code == 404
    assert "Produit inconnu" in r.json()["detail"]


def test_cart_quote_ok(client):
    r = client.post("/cart/quote", json={"items": [{"product_id": "mug", "qty": 2}]})
    assert r.status_code == 200
    assert r.json()["subtotal"] == "25.00"
    assert r.json()["shipping"] == "4.90"
    assert r.json()["total"] == "29.90"


def test_cart_quote_coupon(client):
    r = client.post(
        "/cart/quote",
        json={"items": [{"product_id": "mug", "qty": 2}], "coupon": "WELCOME10"},
    )
    assert r.status_code == 200
    assert r.json()["discount"] == "2.50"
    assert r.json()["shipping"] == "4.90"
    assert r.json()["total"] == "27.40"


def test_cart_quote_produit_inconnu(client):
    r = client.post("/cart/quote", json={"items": [{"product_id": "inconnu", "qty": 1}]})
    assert r.status_code == 404
    assert r.json()["detail"] == "Produit inconnu : inconnu"


def test_cart_quote_quantite_invalide(client):
    r = client.post("/cart/quote", json={"items": [{"product_id": "mug", "qty": 0}]})
    assert r.status_code == 422


def test_create_order(client):
    r = client.post("/orders", json={"items": [{"product_id": "mug", "qty": 1}]})
    assert r.status_code == 201
    body = r.json()
    assert body["id"]
    assert body["total"] == "17.40"


def test_create_order_panier_vide(client):
    r = client.post("/orders", json={"items": []})
    assert r.status_code == 422
    assert r.json()["detail"] == "Panier vide"


def test_get_order(client):
    create = client.post("/orders", json={"items": [{"product_id": "mug", "qty": 1}]})
    order_id = create.json()["id"]

    r = client.get(f"/orders/{order_id}")
    assert r.status_code == 200
    assert r.json()["id"] == order_id


# TODO Atelier 9 : /products/{id} (200, 404), /cart/quote (200, 404, 422), /orders (201, 422), GET /orders/{id}
