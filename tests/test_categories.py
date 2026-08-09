"""Tests for the /categories endpoints."""


def test_create_category(client, category_payload):
    response = client.post("/categories", json=category_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == category_payload["name"]
    assert data["description"] == category_payload["description"]
    assert "id" in data


def test_create_duplicate_category(client, category_payload):
    client.post("/categories", json=category_payload)
    response = client.post("/categories", json=category_payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["message"].lower()


def test_list_categories_empty(client):
    response = client.get("/categories")
    assert response.status_code == 200
    assert response.json() == []


def test_list_categories(client, category_payload):
    client.post("/categories", json=category_payload)
    response = client.get("/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == category_payload["name"]
