"""data/settings.py — App settings stored in the AppSettings key-value table.

Educational patterns:
- INSERT OR REPLACE as an upsert / key-value store
- Simple abstraction layer over raw sqlite3
"""
from db import get_connection


def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    row = conn.execute("SELECT value FROM AppSettings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO AppSettings (key, value) VALUES (?,?)",
        (key, value),
    )
    conn.commit()
    conn.close()


def get_currency_symbol() -> str:
    return get_setting("currency_symbol", "$")
