from __future__ import annotations
"""data/regions.py — SQL-only data access for Regions and Territories."""
from db import get_connection


# ── Regions ──────────────────────────────────────────────────────────────────

def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT RegionID, RegionDescription FROM Region ORDER BY RegionID"
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def fetch_for_picker() -> list:
    return fetch_all()


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM Region WHERE RegionID=?", (pk,)).fetchone()
    conn.close()
    return dict(row) if row else None


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        "SELECT RegionID, RegionDescription FROM Region "
        "WHERE RegionDescription LIKE ? ORDER BY RegionDescription",
        (like,),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def insert(data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO Region (RegionDescription) VALUES (?)",
        (data.get("RegionDescription"),),
    )
    conn.commit()
    conn.close()


def update(pk, data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE Region SET RegionDescription=? WHERE RegionID=?",
        (data.get("RegionDescription"), pk),
    )
    conn.commit()
    conn.close()


def delete(pk) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM Region WHERE RegionID=?", (pk,))
    conn.commit()
    conn.close()


# ── Territories ───────────────────────────────────────────────────────────────

def fetch_territories() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT t.TerritoryID, t.TerritoryDescription, r.RegionDescription
           FROM Territories t
           JOIN Region r ON t.RegionID = r.RegionID
           ORDER BY t.TerritoryID"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def search_territories(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        """SELECT t.TerritoryID, t.TerritoryDescription, r.RegionDescription
           FROM Territories t JOIN Region r ON t.RegionID=r.RegionID
           WHERE t.TerritoryDescription LIKE ? OR t.TerritoryID LIKE ?
           ORDER BY t.TerritoryDescription""",
        (like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_territory_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT t.*, r.RegionDescription
           FROM Territories t JOIN Region r ON t.RegionID=r.RegionID
           WHERE t.TerritoryID=?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_territory(data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO Territories (TerritoryID, TerritoryDescription, RegionID) VALUES (?,?,?)",
        (data.get("TerritoryID"), data.get("TerritoryDescription"), data.get("RegionID")),
    )
    conn.commit()
    conn.close()


def update_territory(pk, data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE Territories SET TerritoryDescription=?, RegionID=? WHERE TerritoryID=?",
        (data.get("TerritoryDescription"), data.get("RegionID"), pk),
    )
    conn.commit()
    conn.close()


def delete_territory(pk) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM Territories WHERE TerritoryID=?", (pk,))
    conn.commit()
    conn.close()
