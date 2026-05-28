import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "toponecashier.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path: str = None) -> sqlite3.Connection:
    path = db_path or str(DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()
