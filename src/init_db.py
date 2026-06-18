import sqlite3
from pathlib import Path


def initialize_database(db_path="store.db", schema_file="store_schema.sql"):
    """Create and seed the SQLite database when it does not exist."""
    db_path = Path(db_path)
    schema_file = Path(schema_file)
    db_exists = db_path.exists()
    conn = None

    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        if not db_exists:
            with schema_file.open("r", encoding="utf-8") as file:
                schema_script = file.read()

            cursor.executescript(schema_script)
            conn.commit()
            print(f"Created database at {db_path}.")
        else:
            print(f"Using existing database at {db_path}.")

    except sqlite3.Error as exc:
        print(f"Database initialization error: {exc}")
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    initialize_database(base_dir / "store.db", base_dir / "store_schema.sql")
