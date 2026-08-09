"""Tests for the bulk-update and adjust-stock endpoints."""


def make_product(client, product_payload, **overrides):
    payload = {**product_payload, **overrides}
    return client.post("/products", json=payload).json()


# ---------------------------------------------------------------------
# PATCH /products/bulk-update
# ---------------------------------------------------------------------


def test_bulk_update_applies_discount(client, product_payload):
    make_product(client, product_payload, sku="LAP-TOP-0001", price=1000)

    response = client.patch(
        "/products/bulk-update",
        params={"category": "Laptops", "discount_percent": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["updated_count"] == 1
    assert data["category"] == "Laptops"

    updated = client.get("/products").json()[0]
    assert updated["price"] == 900.0


def test_bulk_update_skips_products_below_price_floor(client, product_payload):
    # A steep discount on a cheap item would drop it below the 100 floor,
    # so it should be skipped rather than updated.
    make_product(client, product_payload, sku="LAP-TOP-0002", price=105)

    response = client.patch(
        "/products/bulk-update",
        params={"category": "Laptops", "discount_percent": 50},
    )
    assert response.status_code == 200
    assert response.json()["updated_count"] == 0


def test_bulk_update_invalid_discount(client):
    response = client.patch(
        "/products/bulk-update",
        params={"category": "Laptops", "discount_percent": 0},
    )
    assert response.status_code == 400


def test_bulk_update_discount_over_100(client):
    response = client.patch(
        "/products/bulk-update",
        params={"category": "Laptops", "discount_percent": 150},
    )
    assert response.status_code == 400


def test_bulk_update_no_matching_products(client):
    response = client.patch(
        "/products/bulk-update",
        params={"category": "Nonexistent", "discount_percent": 10},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------
# PATCH /products/adjust-stock
# ---------------------------------------------------------------------


def test_adjust_stock_success(client, product_payload):
    product = make_product(client, product_payload, sku="LAP-TOP-0003", stock=10)

    response = client.patch(
        "/products/adjust-stock",
        json=[{"product_id": product["id"], "quantity_to_add": 15}],
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["success"]) == 1
    assert data["success"][0]["new_stock"] == 25
    assert data["failed"] == []


def test_adjust_stock_product_not_found(client):
    response = client.patch(
        "/products/adjust-stock",
        json=[{"product_id": 99999, "quantity_to_add": 5}],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == []
    assert data["failed"][0]["reason"] == "Product not found"


def test_adjust_stock_exceeds_limit(client, product_payload):
    product = make_product(client, product_payload, sku="LAP-TOP-0004", stock=4990)

    response = client.patch(
        "/products/adjust-stock",
        json=[{"product_id": product["id"], "quantity_to_add": 100}],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == []
    assert data["failed"][0]["reason"] == "Stock exceeds limit"


def test_adjust_stock_mixed_batch(client, product_payload):
    ok_product = make_product(client, product_payload, sku="LAP-TOP-0005", stock=10)

    response = client.patch(
        "/products/adjust-stock",
        json=[
            {"product_id": ok_product["id"], "quantity_to_add": 5},
            {"product_id": 99999, "quantity_to_add": 5},
        ],
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["success"]) == 1
    assert len(data["failed"]) == 1


def test_adjust_stock_rejects_non_positive_quantity(client, product_payload):
    product = make_product(client, product_payload, sku="LAP-TOP-0006")

    response = client.patch(
        "/products/adjust-stock",
        json=[{"product_id": product["id"], "quantity_to_add": 0}],
    )
    assert response.status_code == 422
