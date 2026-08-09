"""
Exercise 2: Load test with Locust.

Start your API first (e.g. `uvicorn main:app`), then run:
    locust -f locustfile.py --host http://localhost:8000

Open http://localhost:8089 to set concurrent users / spawn rate and
watch requests/sec, response times, and failure rate live.
"""

import random

from locust import HttpUser, between, task


class InventoryUser(HttpUser):
    wait_time = between(0.2, 1.0)

    @task(3)
    def list_products(self):
        self.client.get("/products")

    @task(1)
    def create_product(self):
        n = random.randint(1, 999999)
        self.client.post(
            "/products",
            json={
                "name": "Load Test Product",
                "description": "Created by locust load test",
                "brand": "LoadCo",
                "category": "LoadTest",
                "price": 199.99,
                "stock": 10,
                "warranty_months": 12,
                "sku": f"LOA-DTS-{n % 10000:04d}",
            },
        )

    @task(1)
    def health_check(self):
        self.client.get("/health")
