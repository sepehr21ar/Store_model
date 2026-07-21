from sqlalchemy import inspect, text

from .database import engine


def migrate_schema() -> None:
    """Apply small, idempotent migrations needed by existing deployments."""
    if "users" not in inspect(engine).get_table_names():
        return

    if engine.dialect.name == "postgresql":
        # IF NOT EXISTS keeps concurrent FastAPI Cloud instance startups safe.
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(120)"))
            connection.execute(text("UPDATE users SET name = 'User' WHERE name IS NULL OR BTRIM(name) = ''"))
            connection.execute(text("ALTER TABLE users ALTER COLUMN name SET NOT NULL"))
        return

    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    if "name" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR(120)"))
            connection.execute(text("UPDATE users SET name = 'User' WHERE name IS NULL OR TRIM(name) = ''"))
