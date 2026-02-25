from __future__ import annotations

"""data/categories.py — SQL-only data access for Categories."""
from db import get_connection


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT CategoryID, CategoryName, Description FROM Categories ORDER BY CategoryID"
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def fetch_for_picker() -> list:
    return fetch_all()


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM Categories WHERE CategoryID=?", (pk,)).fetchone()
    conn.close()
    return dict(row) if row else None


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        "SELECT CategoryID, CategoryName, Description FROM Categories "
        "WHERE CategoryName LIKE ? OR Description LIKE ? ORDER BY CategoryName",
        (like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def insert(data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO Categories (CategoryName, Description) VALUES (?,?)",
        (data.get("CategoryName"), data.get("Description") or None),
    )
    conn.commit()
    conn.close()


def update(pk, data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE Categories SET CategoryName=?, Description=? WHERE CategoryID=?",
        (data.get("CategoryName"), data.get("Description") or None, pk),
    )
    conn.commit()
    conn.close()


def delete(pk) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM Categories WHERE CategoryID=?", (pk,))
    conn.commit()
    conn.close()
