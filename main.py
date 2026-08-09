import logging
import platform
import time
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from contextlib import asynccontextmanager

from database.session import create_db_and_tables, get_session
from models.product import (
    Category,
    CategoryCreate,
    Product,
    ProductCreate,
    ProductUpdate,
    StockAdjustment,
    Supplier,
    SupplierCreate,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="TechVault Inventory API", version="1.0.0", lifespan=lifespan)

START_TIME = time.time()

# LOGGING + ERROR RESPONSE FORMAT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - Time: {duration:.3f}s"
    )
    return response


@app.get("/health")
def health_check():
    """Lightweight liveness/readiness probe for uptime monitors."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": app.version,
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "python": platform.python_version(),
    }


@app.get("/metrics")
def get_metrics(session: Session = Depends(get_session)):
    """Basic inventory metrics, useful as a custom monitoring signal."""
    product_count = len(session.exec(select(Product)).all())
    category_count = len(session.exec(select(Category)).all())
    supplier_count = len(session.exec(select(Supplier)).all())
    return {
        "product_count": product_count,
        "category_count": category_count,
        "supplier_count": supplier_count,
        "uptime_seconds": round(time.time() - START_TIME, 2),
    }


def error_response(success: bool, status_code: int, message: str, path: str, errors=None):
    return {
        "success": success,
        "status_code": status_code,
        "message": message,
        "errors": errors,
        "timestamp": datetime.now(UTC).isoformat(),
        "path": path,
    }


# GLOBAL EXCEPTION HANDLERS


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP Exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(False, exc.status_code, exc.detail, request.url.path),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {
            "field": ".".join(str(loc) for loc in e["loc"]),
            "message": e["msg"],
            "type": e["type"],
        }
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_response(False, 422, "Validation error", request.url.path, errors),
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.error(f"Integrity error: {exc}")
    return JSONResponse(
        status_code=409,
        content=error_response(
            False, 409, "Duplicate entry or constraint violation", request.url.path
        ),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=error_response(False, 500, "An internal error occurred", request.url.path),
    )


@app.post("/categories", response_model=Category, status_code=201)
def create_category(category: CategoryCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(Category).where(Category.name == category.name)).first()

    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")

    db_category = Category(**category.model_dump())

    session.add(db_category)
    session.commit()
    session.refresh(db_category)

    return db_category


@app.get("/categories", response_model=list[Category])
def list_categories(session: Session = Depends(get_session)):
    return session.exec(select(Category)).all()


# PRODUCT CRUD ENDPOINTS
@app.post("/products", response_model=Product, status_code=201)
def create_product(product: ProductCreate, session: Session = Depends(get_session)):

    if product.category_id is not None:
        category = session.get(Category, product.category_id)

        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    db_product = Product(**product.model_dump())

    session.add(db_product)
    session.commit()
    session.refresh(db_product)

    return db_product


@app.get("/products", response_model=list[Product])
def list_products(session: Session = Depends(get_session)):
    return session.exec(select(Product)).all()


# BULK UPDATE ENDPOINT
# NOTE: these two routes must stay ABOVE the /products/{product_id} routes
# below. FastAPI/Starlette match routes in declaration order, so a literal
# path like /products/bulk-update must be registered before the parameterized
# /products/{product_id} pattern, or "bulk-update"/"adjust-stock" get matched
# to {product_id} and fail int validation with a 422.


@app.patch("/products/bulk-update")
def bulk_update_price(
    category: str, discount_percent: float, session: Session = Depends(get_session)
):
    if discount_percent <= 0 or discount_percent > 100:
        raise HTTPException(400, "Discount percent must be between 0 and 100")

    products = session.exec(select(Product).where(Product.category == category)).all()
    if not products:
        raise HTTPException(404, "No products found in this category")

    updated = []
    for product in products:
        new_price = round(product.price * (1 - discount_percent / 100), 2)
        if new_price < 100:
            continue
        product.price = new_price
        product.updated_at = datetime.now(UTC)
        updated.append(product)

    session.commit()
    return {
        "updated_count": len(updated),
        "category": category,
        "discount": discount_percent,
    }


# STOCK ADJUSTMENT ENDPOINT


@app.patch("/products/adjust-stock")
def adjust_stock(adjustments: list[StockAdjustment], session: Session = Depends(get_session)):
    results = {"success": [], "failed": []}
    for adj in adjustments:
        product = session.get(Product, adj.product_id)
        if not product:
            results["failed"].append({"product_id": adj.product_id, "reason": "Product not found"})
            continue
        new_stock = product.stock + adj.quantity_to_add
        if new_stock > 5000:
            results["failed"].append(
                {"product_id": adj.product_id, "reason": "Stock exceeds limit"}
            )
            continue
        product.stock = new_stock
        product.updated_at = datetime.now(UTC)
        results["success"].append({"product_id": adj.product_id, "new_stock": new_stock})
    session.commit()
    return results


@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@app.patch("/products/{product_id}", response_model=Product)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    session: Session = Depends(get_session),
):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    for key, value in product_update.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    product.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(product)
    return product


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    session.delete(product)
    session.commit()


# SUPPLIER CRUD ENDPOINTS


@app.post("/suppliers", response_model=Supplier, status_code=201)
def create_supplier(supplier: SupplierCreate, session: Session = Depends(get_session)):
    db_supplier = Supplier(**supplier.model_dump())
    session.add(db_supplier)
    session.commit()
    session.refresh(db_supplier)
    return db_supplier


@app.get("/suppliers", response_model=list[Supplier])
def list_suppliers(session: Session = Depends(get_session)):
    return session.exec(select(Supplier)).all()
