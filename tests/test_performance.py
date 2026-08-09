"""
Exercise 2: Lightweight in-process benchmark using pytest-benchmark.
Run with:  pytest tests/test_performance.py --benchmark-only

For real network-level load testing (concurrent users, requests/sec
against a running server) see locustfile.py in the project root and
run: locust -f locustfile.py --host http://localhost:8000
"""

import pytest


@pytest.mark.benchmark
def test_create_product_performance(client, benchmark):
    counter = {"n": 0}

    def create_product():
        counter["n"] += 1
        payload = {
            "name": "Benchmark Product",
            "description": "Product created during benchmarking",
            "brand": "BenchCo",
            "category": "Benchmark",
            "price": 199.99,
            "stock": 5,
            "warranty_months": 12,
            "sku": f"BEN-CHM-{counter['n']:04d}",
        }
        response = client.post("/products", json=payload)
        assert response.status_code == 201

    benchmark(create_product)


@pytest.mark.benchmark
def test_list_products_performance(client, product_payload, benchmark):
    client.post("/products", json=product_payload)

    def list_products():
        response = client.get("/products")
        assert response.status_code == 200

    benchmark(list_products)
