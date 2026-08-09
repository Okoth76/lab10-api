"""Tests for the /suppliers endpoints."""

import pytest


def test_create_supplier(client, supplier_payload):
    response = client.post("/suppliers", json=supplier_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == supplier_payload["name"]
    assert data["email"] == supplier_payload["email"]
    assert data["is_active"] is True


def test_list_suppliers(client, supplier_payload):
    client.post("/suppliers", json=supplier_payload)
    response = client.get("/suppliers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == supplier_payload["name"]


@pytest.mark.parametrize("bad_email", ["not-an-email", "missing-at-sign.com", "no-domain@"])
def test_create_supplier_invalid_email(client, supplier_payload, bad_email):
    supplier_payload["email"] = bad_email
    response = client.post("/suppliers", json=supplier_payload)
    assert response.status_code == 422


@pytest.mark.parametrize("bad_phone", ["abc123", "555", "+"])
def test_create_supplier_invalid_phone(client, supplier_payload, bad_phone):
    supplier_payload["phone"] = bad_phone
    response = client.post("/suppliers", json=supplier_payload)
    assert response.status_code == 422
