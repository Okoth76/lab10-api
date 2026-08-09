"""Tests for the /products CRUD endpoints and their validation rules."""


def test_create_product(client, product_payload):
    response = client.post("/products", json=product_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == product_payload["name"]
    assert data["sku"] == product_payload["sku"]
    assert "id" in data


def test_create_product_with_category_id(client, category_payload, product_payload):
    cat = client.post("/categories", json=category_payload).json()
    product_payload["category_id"] = cat["id"]
    response = client.post("/products", json=product_payload)
    assert response.status_code == 201
    assert response.json()["category_id"] == cat["id"]


def test_create_product_invalid_category_id(client, product_payload):
    product_payload["category_id"] = 9999
    response = client.post("/products", json=product_payload)
    assert response.status_code == 404


def test_create_product_name_must_start_capital(client, product_payload):
    product_payload["name"] = "thinkpad x1"
    response = client.post("/products", json=product_payload)
    assert response.status_code == 422


def test_create_product_price_below_minimum(client, product_payload):
    product_payload["price"] = 50
    response = client.post("/products", json=product_payload)
    assert response.status_code == 422


def test_create_product_invalid_sku_format(client, product_payload):
    product_payload["sku"] = "not-a-valid-sku"
    response = client.post("/products", json=product_payload)
    assert response.status_code == 422


def test_create_product_high_value_requires_warranty(client, product_payload):
    product_payload["price"] = 60000
    product_payload["warranty_months"] = 6
    response = client.post("/products", json=product_payload)
    assert response.status_code == 422


def test_create_product_high_value_with_sufficient_warranty(client, product_payload):
    product_payload["price"] = 60000
    product_payload["warranty_months"] = 12
    response = client.post("/products", json=product_payload)
    assert response.status_code == 201


def test_create_product_duplicate_sku(client, product_payload):
    client.post("/products", json=product_payload)
    duplicate = product_payload.copy()
    duplicate["name"] = "Different Name"
    response = client.post("/products", json=duplicate)
    assert response.status_code == 409


def test_list_products(client, product_payload):
    client.post("/products", json=product_payload)
    response = client.get("/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["sku"] == product_payload["sku"]


def test_get_product(client, product_payload):
    created = client.post("/products", json=product_payload).json()
    response = client.get(f"/products/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == product_payload["name"]


def test_get_product_not_found(client):
    response = client.get("/products/99999")
    assert response.status_code == 404


def test_update_product(client, product_payload):
    created = client.post("/products", json=product_payload).json()
    response = client.patch(
        f"/products/{created['id']}",
        json={"name": "Thinkpad X1 Gen2", "price": 1599.99},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Thinkpad X1 Gen2"
    assert data["price"] == 1599.99


def test_update_product_not_found(client):
    response = client.patch("/products/99999", json={"name": "Ghost"})
    assert response.status_code == 404


def test_delete_product(client, product_payload):
    created = client.post("/products", json=product_payload).json()
    response = client.delete(f"/products/{created['id']}")
    assert response.status_code == 204

    follow_up = client.get(f"/products/{created['id']}")
    assert follow_up.status_code == 404


def test_delete_product_not_found(client):
    response = client.delete("/products/99999")
    assert response.status_code == 404
