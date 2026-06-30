import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


def database_url() -> str:
    load_dotenv()
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not configured.")
    return url


def initialize_database(schema_file: str | Path) -> None:
    """Create PostgreSQL tables, constraints, triggers, and seed data."""
    schema_path = Path(schema_file)
    schema_script = schema_path.read_text(encoding="utf-8")

    with psycopg.connect(database_url()) as conn:
        with conn.cursor() as cursor:
            cursor.execute(schema_script)
        conn.commit()

    print("PostgreSQL database initialized.")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    initialize_database(base_dir / "store_schema_postgres.sql")
