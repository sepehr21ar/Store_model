import io
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .ai_service import answer_question
from .analytics import chart_data, create_dataset, dataframe, dataset_summary, json_value, owned_dataset, profile_for_ai
from .database import Base, engine, get_db
from .migrations import migrate_schema
from .models import ChatMessage, Dashboard, Dataset, DatasetRow, User
from .security import create_token, current_user, hash_password, verify_password


load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ChartRequest(BaseModel):
    category: str | None = None
    value: str
    aggregation: str = "sum"
    chart_type: Literal["bar", "line"] = "bar"
    limit: int = Field(default=12, ge=1, le=50)


class DashboardRequest(BaseModel):
    dataset_id: int
    name: str = Field(min_length=1, max_length=180)
    config: list[dict] = Field(default_factory=list)


class ChatRequest(BaseModel):
    dataset_id: int
    message: str = Field(min_length=1, max_length=4000)


def dataset_dict(item: Dataset) -> dict:
    return {"id": item.id, "name": item.name, "source_type": item.source_type, "source_label": item.source_label, "columns": item.columns, "row_count": item.row_count, "created_at": item.created_at}


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    yield


app = FastAPI(title="Prism Analytics API", version="3.0.0", lifespan=lifespan)
origins = [item.strip() for item in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if item.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "prism-analytics"}


@app.post("/api/auth/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists.")
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_token(user.id), "token_type": "bearer", "user": {"id": user.id, "name": user.name, "email": user.email}}


@app.post("/api/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username.lower().strip()))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password.")
    return {"access_token": create_token(user.id), "token_type": "bearer", "user": {"id": user.id, "name": user.name, "email": user.email}}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "name": user.name, "email": user.email}


@app.get("/api/datasets")
def list_datasets(user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Dataset).where(Dataset.user_id == user.id).order_by(Dataset.created_at.desc())).all()
    return {"items": [dataset_dict(item) for item in items]}


@app.post("/api/datasets/upload", status_code=201)
async def upload_dataset(name: str | None = Form(None), file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in {".xlsx", ".xls", ".csv", ".txt", ".tsv"}:
        raise HTTPException(400, "Supported files are .xlsx, .xls, .csv, .tsv, and .txt.")
    content = await file.read()
    if not content:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(content) > int(os.getenv("MAX_UPLOAD_MB", "25")) * 1024 * 1024:
        raise HTTPException(413, "File is too large.")
    try:
        if extension in {".csv", ".txt", ".tsv"}:
            separator = "\t" if extension == ".tsv" else None
            try:
                frame = pd.read_csv(io.BytesIO(content), sep=separator, engine="python", encoding="utf-8-sig")
            except UnicodeDecodeError:
                frame = pd.read_csv(io.BytesIO(content), sep=separator, engine="python", encoding="latin-1")
        else:
            engine_name = "openpyxl" if extension == ".xlsx" else "xlrd"
            frame = pd.read_excel(io.BytesIO(content), engine=engine_name)
    except ImportError as exc:
        package = "openpyxl" if extension == ".xlsx" else "xlrd"
        raise HTTPException(503, f"Excel support is not installed on the server. Install the '{package}' dependency and restart the app.") from exc
    except Exception as exc:
        raise HTTPException(400, "Could not read this file. Check that it is not corrupted and that the first row contains column names.") from exc
    dataset_name = (name or "").strip() or Path(file.filename or "Dataset").stem
    item = create_dataset(db, user.id, dataset_name, frame, "file", file.filename)
    return dataset_dict(item)


@app.get("/api/datasets/{dataset_id}")
def get_dataset(dataset_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = owned_dataset(db, dataset_id, user.id)
    frame = dataframe(db, item)
    return {**dataset_dict(item), "summary": dataset_summary(frame, item.columns)}


@app.get("/api/datasets/{dataset_id}/rows")
def get_rows(dataset_id: int, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=1000), user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = owned_dataset(db, dataset_id, user.id)
    rows = db.scalars(select(DatasetRow).where(DatasetRow.dataset_id == item.id).order_by(DatasetRow.position).offset(offset).limit(limit)).all()
    return {"items": [row.payload for row in rows], "total": item.row_count, "offset": offset, "limit": limit}


@app.get("/api/datasets/{dataset_id}/export")
def export_dataset(dataset_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = owned_dataset(db, dataset_id, user.id)
    content = dataframe(db, item).to_csv(index=False).encode("utf-8-sig")
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", item.name).strip("-.") or f"dataset-{item.id}"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.csv"'},
    )


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = owned_dataset(db, dataset_id, user.id)
    db.execute(delete(ChatMessage).where(ChatMessage.dataset_id == item.id, ChatMessage.user_id == user.id))
    db.execute(delete(Dashboard).where(Dashboard.dataset_id == item.id, Dashboard.user_id == user.id))
    db.execute(delete(DatasetRow).where(DatasetRow.dataset_id == item.id))
    db.delete(item)
    db.commit()
    return {"message": "Dataset deleted.", "dataset_id": dataset_id}


@app.post("/api/datasets/{dataset_id}/chart")
def analyze_chart(dataset_id: int, payload: ChartRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = owned_dataset(db, dataset_id, user.id)
    if payload.chart_type == "line" and not payload.category:
        raise HTTPException(400, "Select a category or date column for the line chart X axis.")
    return chart_data(dataframe(db, item), payload.category, payload.value, payload.aggregation, payload.limit, payload.chart_type)


@app.get("/api/dashboards")
def list_dashboards(dataset_id: int | None = Query(None, ge=1), user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(Dashboard).where(Dashboard.user_id == user.id)
    if dataset_id is not None:
        owned_dataset(db, dataset_id, user.id)
        query = query.where(Dashboard.dataset_id == dataset_id)
    items = db.scalars(query.order_by(Dashboard.created_at.desc())).all()
    return {"items": [{"id": item.id, "dataset_id": item.dataset_id, "name": item.name, "config": item.config, "created_at": item.created_at} for item in items]}


@app.post("/api/dashboards", status_code=201)
def save_dashboard(payload: DashboardRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_dataset(db, payload.dataset_id, user.id)
    item = Dashboard(user_id=user.id, dataset_id=payload.dataset_id, name=payload.name.strip(), config=payload.config)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "name": item.name, "config": item.config}


@app.post("/api/chat")
def chat(payload: ChatRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = owned_dataset(db, payload.dataset_id, user.id)
    messages = db.scalars(select(ChatMessage).where(ChatMessage.user_id == user.id, ChatMessage.dataset_id == item.id).order_by(ChatMessage.created_at.desc()).limit(8)).all()
    history = [{"role": row.role, "content": row.content} for row in reversed(messages)]
    db.add(ChatMessage(user_id=user.id, dataset_id=item.id, role="user", content=payload.message.strip()))
    try:
        result = answer_question(payload.message.strip(), item.name, profile_for_ai(dataframe(db, item), item.columns), history)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    db.add(ChatMessage(user_id=user.id, dataset_id=item.id, role="assistant", content=result["answer"], visual=result["chart"]))
    db.commit()
    return result


@app.get("/api/chat/{dataset_id}")
def chat_history(dataset_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_dataset(db, dataset_id, user.id)
    items = db.scalars(select(ChatMessage).where(ChatMessage.user_id == user.id, ChatMessage.dataset_id == dataset_id).order_by(ChatMessage.created_at).limit(100)).all()
    return {"items": [{"role": item.role, "content": item.content, "chart": item.visual, "created_at": item.created_at} for item in items]}


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "Not found")
    asset = STATIC_DIR / path
    return FileResponse(asset if asset.is_file() else STATIC_DIR / "index.html")