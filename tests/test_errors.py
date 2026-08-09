"""Tests for the global exception handlers and error response shape."""


def test_404_unknown_route(client):
    response = client.get("/non-existent-endpoint")
    assert response.status_code == 404


def test_error_response_shape(client):
    response = client.get("/products/99999")
    assert response.status_code == 404
    data = response.json()
    # Matches the error_response() shape defined in main.py
    assert data["success"] is False
    assert data["status_code"] == 404
    assert "message" in data
    assert "timestamp" in data
    assert data["path"] == "/products/99999"


def test_validation_error_shape(client, product_payload):
    product_payload["price"] = "not-a-number"
    response = client.post("/products", json=product_payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["status_code"] == 422
    assert isinstance(data["errors"], list)
    assert data["errors"][0]["field"]


def test_duplicate_entry_returns_409(client, product_payload):
    client.post("/products", json=product_payload)
    duplicate = product_payload.copy()
    duplicate["name"] = "Another Name"
    response = client.post("/products", json=duplicate)
    assert response.status_code == 409
    assert response.json()["success"] is False
