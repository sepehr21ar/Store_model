import os
import warnings
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


load_dotenv()


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./analytics.db").strip()
    host = urlparse(url).hostname
    if host == "replace_host":
        warnings.warn(
            "DATABASE_URL still uses the replace_host template value; using local SQLite instead.",
            RuntimeWarning,
            stacklevel=2,
        )
        return "sqlite:///./analytics.db"
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = database_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
