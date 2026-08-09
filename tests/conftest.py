"""
Shared pytest fixtures for the TechVault Inventory API test suite.

Each test gets a fresh, isolated in-memory SQLite database via the
`client` fixture, which overrides the app's `get_session` dependency.
Using StaticPool keeps the same in-memory DB alive across the
multiple connections a single test may open.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from database.session import get_session
from main import app


@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh in-memory SQLite engine + session for a single test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """FastAPI TestClient wired to the isolated test session."""

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------
# Reusable sample payloads
# ---------------------------------------------------------------------


@pytest.fixture
def category_payload():
    return {"name": "Laptops", "description": "Portable computers"}


@pytest.fixture
def supplier_payload():
    return {
        "name": "Acme Supplies",
        "contact_person": "Jane Doe",
        "email": "jane@acmesupplies.com",
        "phone": "+15551234567",
    }


@pytest.fixture
def product_payload():
    return {
        "name": "Thinkpad X1",
        "description": "Business ultrabook",
        "brand": "Lenovo",
        "category": "Laptops",
        "price": 1499.99,
        "stock": 25,
        "warranty_months": 24,
        "sku": "LAP-TOP-0001",
    }
