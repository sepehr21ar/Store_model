import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Generator, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .init_db import initialize_database
from .store import StoreApp


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
SCHEMA_PATH = BASE_DIR / "store_schema.sql"
STATIC_DIR = BASE_DIR / "static"


def is_writable(path: Path) -> bool:
    return path.exists() and os.access(path, os.W_OK)


def default_db_path() -> Path:
    data_dir = Path("/data")
    if is_writable(data_dir):
        return data_dir / "store.db"
    return BASE_DIR / "store.db"


DB_PATH = Path(os.getenv("STORE_DB_PATH", str(default_db_path())))
ACTION_LOG_PATH = Path(
    os.getenv(
        "ACTION_LOG_PATH",
        str((Path("/data") if is_writable(Path("/data")) else ROOT_DIR) / "action_flag.txt"),
    )
)


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    price: float = Field(gt=0)


class QuantityChange(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class ProductStatusUpdate(BaseModel):
    active: bool


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)


def log_action(action: str) -> None:
    ACTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with ACTION_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {action}\n")


def get_store() -> Generator[StoreApp, None, None]:
    store_app = StoreApp(str(DB_PATH))
    store_app.start()
    try:
        yield store_app
    finally:
        store_app.stop()


def report_row_to_dict(row: tuple) -> dict:
    return {
        "product_id": row[0],
        "name": row[1],
        "price": float(row[2]),
        "inventory": int(row[3] or 0),
        "store_sales": int(row[4] or 0),
        "online_sales": int(row[5] or 0),
        "total_sales": int(row[6] or 0),
        "active": bool(row[7]),
    }


def inventory_row_to_dict(row: tuple) -> dict:
    return {
        "product_id": row[0],
        "name": row[1],
        "price": float(row[2]),
        "quantity": int(row[3] or 0),
        "active": bool(row[7]),
    }


def get_report_rows(store_app: StoreApp) -> list[tuple]:
    return store_app.report.get_sales_report()


def ensure_product_exists(store_app: StoreApp, product_id: int) -> None:
    if not store_app.store.check_product_exists(product_id):
        raise HTTPException(status_code=404, detail=f"Product {product_id} was not found.")


def handle_operation_error(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail=str(exc)) from exc


@asynccontextmanager
async def lifespan(_: FastAPI):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    initialize_database(str(DB_PATH), str(SCHEMA_PATH))
    yield


app = FastAPI(
    title="Store Management API",
    version="2.0.0",
    lifespan=lifespan,
)

cors_origins = [origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if origin.strip()]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "database": str(DB_PATH)}


@app.get("/api/dashboard")
def dashboard(store_app: StoreApp = Depends(get_store)) -> dict:
    rows = [report_row_to_dict(row) for row in get_report_rows(store_app)]
    total_inventory = sum(row["inventory"] for row in rows)
    store_sales = sum(row["store_sales"] for row in rows)
    online_sales = sum(row["online_sales"] for row in rows)
    inventory_value = sum(row["price"] * row["inventory"] for row in rows)

    return {
        "total_products": len(rows),
        "active_products": sum(1 for row in rows if row["active"]),
        "inventory_units": total_inventory,
        "store_sales": store_sales,
        "online_sales": online_sales,
        "total_sales": store_sales + online_sales,
        "inventory_value": round(inventory_value, 2),
    }


@app.get("/api/products")
def list_products(store_app: StoreApp = Depends(get_store)) -> dict:
    items = [report_row_to_dict(row) for row in get_report_rows(store_app)]
    return {"items": items, "count": len(items)}


@app.post("/api/products", status_code=201)
def create_product(payload: ProductCreate, store_app: StoreApp = Depends(get_store)) -> dict:
    try:
        product_id = store_app.add_new_product(payload.name.strip(), payload.price)
        log_action(f"ProductAdded: ID={product_id} Name={payload.name.strip()}")
        return {"message": "Product added.", "product_id": product_id}
    except Exception as exc:
        handle_operation_error(exc)


@app.patch("/api/products/{product_id}/status")
def update_product_status(
    product_id: int,
    payload: ProductStatusUpdate,
    store_app: StoreApp = Depends(get_store),
) -> dict:
    ensure_product_exists(store_app, product_id)
    try:
        if payload.active:
            store_app.storage.activate_product(product_id)
            action = "ProductActivated"
            message = "Product activated."
        else:
            store_app.storage.delete_product(product_id)
            action = "ProductDeactivated"
            message = "Product deactivated."

        log_action(f"{action}: ID={product_id}")
        return {"message": message, "product_id": product_id, "active": payload.active}
    except Exception as exc:
        handle_operation_error(exc)


@app.get("/api/inventory")
def list_inventory(store_app: StoreApp = Depends(get_store)) -> dict:
    items = [inventory_row_to_dict(row) for row in get_report_rows(store_app)]
    return {"items": items, "count": len(items)}


@app.post("/api/inventory")
def add_inventory(payload: QuantityChange, store_app: StoreApp = Depends(get_store)) -> dict:
    ensure_product_exists(store_app, payload.product_id)
    try:
        store_app.add_product_to_inventory(payload.product_id, payload.quantity)
        product = store_app.get_product_by_id(payload.product_id)
        product_name = product.name if product else "Unknown"
        log_action(f"InventoryUpdated: ID={payload.product_id}({product_name}) QTY={payload.quantity}")
        return {"message": "Inventory updated.", "product_id": payload.product_id, "quantity": payload.quantity}
    except Exception as exc:
        handle_operation_error(exc)


@app.post("/api/sales/store")
def record_store_sale(payload: QuantityChange, store_app: StoreApp = Depends(get_store)) -> dict:
    ensure_product_exists(store_app, payload.product_id)
    try:
        store_app.record_store_sale(payload.product_id, payload.quantity)
        product = store_app.get_product_by_id(payload.product_id)
        product_name = product.name if product else "Unknown"
        log_action(f"StoreSale: ID={payload.product_id}({product_name}) QTY={payload.quantity}")
        return {"message": "Store sale recorded.", "product_id": payload.product_id, "quantity": payload.quantity}
    except Exception as exc:
        handle_operation_error(exc)


@app.post("/api/sales/online")
def record_online_sale(payload: QuantityChange, store_app: StoreApp = Depends(get_store)) -> dict:
    ensure_product_exists(store_app, payload.product_id)
    try:
        store_app.record_online_sale(payload.product_id, payload.quantity)
        product = store_app.get_product_by_id(payload.product_id)
        product_name = product.name if product else "Unknown"
        log_action(f"OnlineSale: ID={payload.product_id}({product_name}) QTY={payload.quantity}")
        return {"message": "Online sale recorded.", "product_id": payload.product_id, "quantity": payload.quantity}
    except Exception as exc:
        handle_operation_error(exc)


@app.get("/api/reports/sales")
def sales_report(store_app: StoreApp = Depends(get_store)) -> dict:
    items = [report_row_to_dict(row) for row in get_report_rows(store_app)]
    return {"items": items, "count": len(items)}


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict:
    history = [message.model_dump() for message in payload.history]
    history.append({"role": "user", "content": payload.message.strip()})

    try:
        from .llm_sql import chat_with_llm

        messages, status = chat_with_llm(history)
        return {"messages": messages, "status": status}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{path:path}", include_in_schema=False)
def frontend_fallback(path: str) -> FileResponse:
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    asset_path = STATIC_DIR / path
    if asset_path.is_file():
        return FileResponse(asset_path)

    return FileResponse(STATIC_DIR / "index.html")
