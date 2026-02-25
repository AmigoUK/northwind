from __future__ import annotations

"""data/shippers.py — SQL-only data access for Shippers."""
from db import get_connection


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT ShipperID, CompanyName, Phone FROM Shippers ORDER BY ShipperID"
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def fetch_for_picker() -> list:
    return fetch_all()


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM Shippers WHERE ShipperID=?", (pk,)).fetchone()
    conn.close()
    return dict(row) if row else None


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        "SELECT ShipperID, CompanyName, Phone FROM Shippers "
        "WHERE CompanyName LIKE ? OR Phone LIKE ? ORDER BY CompanyName",
        (like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def insert(data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO Shippers (CompanyName, Phone) VALUES (?,?)",
        (data.get("CompanyName"), data.get("Phone") or None),
    )
    conn.commit()
    conn.close()


def update(pk, data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE Shippers SET CompanyName=?, Phone=? WHERE ShipperID=?",
        (data.get("CompanyName"), data.get("Phone") or None, pk),
    )
    conn.commit()
    conn.close()


def delete(pk) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM Shippers WHERE ShipperID=?", (pk,))
    conn.commit()
    conn.close()
