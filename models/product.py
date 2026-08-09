import re
from datetime import UTC, datetime
from typing import Optional

from pydantic import field_validator, model_validator
from sqlmodel import Field, Relationship, SQLModel

# ==========================================================
# CATEGORY MODELS
# ==========================================================


class Category(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str | None = None

    products: list["Product"] = Relationship(back_populates="category_rel")


class CategoryCreate(SQLModel):
    name: str
    description: str | None = None


# ==========================================================
# SUPPLIER MODELS
# ==========================================================


class Supplier(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    name: str = Field(unique=True, index=True)
    contact_person: str
    email: str = Field(unique=True, index=True)
    phone: str
    is_active: bool = True

    products: list["Product"] = Relationship(back_populates="supplier")


class SupplierCreate(SQLModel):
    name: str
    contact_person: str
    email: str
    phone: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if not re.match(r"^\+?\d{7,15}$", v):
            raise ValueError("Invalid phone number")
        return v


# ==========================================================
# PRODUCT MODEL
# ==========================================================


class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    name: str = Field(index=True)
    description: str

    brand: str
    category: str

    price: float
    stock: int

    warranty_months: int
    sku: str = Field(unique=True, index=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    category_id: int | None = Field(default=None, foreign_key="category.id")

    supplier_id: int | None = Field(default=None, foreign_key="supplier.id")

    category_rel: Optional["Category"] = Relationship(back_populates="products")

    supplier: Optional["Supplier"] = Relationship(back_populates="products")


# ==========================================================
# PRODUCT CREATE
# ==========================================================


class ProductCreate(SQLModel):
    name: str
    description: str
    brand: str
    category: str
    price: float
    stock: int
    warranty_months: int
    sku: str

    category_id: int | None = None
    supplier_id: int | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v[0].isupper():
            raise ValueError("Name must start with a capital letter")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if v < 100:
            raise ValueError("Price must be at least 100")
        return round(v, 2)

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v):
        pattern = r"^[A-Z]{3}-[A-Z]{3}-\d{4}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid SKU format")
        return v

    @model_validator(mode="after")
    def validate_warranty(self):
        if self.price >= 50000 and self.warranty_months < 12:
            raise ValueError("Products over 50,000 must have at least 12 months warranty")
        return self


# ==========================================================
# PRODUCT UPDATE
# ==========================================================


class ProductUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    brand: str | None = None
    category: str | None = None
    price: float | None = None
    stock: int | None = None
    warranty_months: int | None = None
    sku: str | None = None
    category_id: int | None = None
    supplier_id: int | None = None


# ==========================================================
# STOCK ADJUSTMENT
# ==========================================================


class StockAdjustment(SQLModel):
    product_id: int
    quantity_to_add: int = Field(gt=0)
