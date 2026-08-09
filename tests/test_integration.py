"""
Exercise 1: Integration test covering the full lifecycle of a product,
including its supporting category and supplier records, end to end.
"""


def test_full_inventory_flow(client):
    # 1. Create a category
    category = client.post(
        "/categories", json={"name": "Monitors", "description": "Displays"}
    ).json()

    # 2. Create a supplier
    supplier = client.post(
        "/suppliers",
        json={
            "name": "ScreenCo",
            "contact_person": "Alex Kim",
            "email": "alex@screenco.com",
            "phone": "+15559876543",
        },
    ).json()

    # 3. Create a product linked to that category and supplier
    create_resp = client.post(
        "/products",
        json={
            "name": "Ultrawide Monitor",
            "description": "34-inch curved display",
            "brand": "Dell",
            "category": "Monitors",
            "price": 799.99,
            "stock": 15,
            "warranty_months": 24,
            "sku": "MON-DEL-0001",
            "category_id": category["id"],
            "supplier_id": supplier["id"],
        },
    )
    assert create_resp.status_code == 201
    product = create_resp.json()
    assert product["category_id"] == category["id"]

    # 4. Verify it shows up in the product list
    list_resp = client.get("/products")
    assert any(p["id"] == product["id"] for p in list_resp.json())

    # 5. Adjust its stock upward
    adjust_resp = client.patch(
        "/products/adjust-stock",
        json=[{"product_id": product["id"], "quantity_to_add": 10}],
    )
    assert adjust_resp.status_code == 200
    assert adjust_resp.json()["success"][0]["new_stock"] == 25

    # 6. Update its price and name directly
    update_resp = client.patch(
        f"/products/{product['id']}",
        json={"name": "Ultrawide Monitor Pro", "price": 899.99},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Ultrawide Monitor Pro"

    # 7. Apply a bulk discount to its category
    bulk_resp = client.patch(
        "/products/bulk-update",
        params={"category": "Monitors", "discount_percent": 10},
    )
    assert bulk_resp.status_code == 200
    assert bulk_resp.json()["updated_count"] == 1

    # 8. Delete the product and confirm it's gone
    delete_resp = client.delete(f"/products/{product['id']}")
    assert delete_resp.status_code == 204

    final_get = client.get(f"/products/{product['id']}")
    assert final_get.status_code == 404
