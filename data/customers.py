from __future__ import annotations

"""data/customers.py — SQL-only data access for Customers."""
from db import get_connection


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT CustomerID, CompanyName, ContactName, City, Country, Phone "
        "FROM Customers ORDER BY CustomerID"
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def fetch_for_picker() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT CustomerID, CompanyName, ContactName, City "
        "FROM Customers ORDER BY CustomerID"
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM Customers WHERE CustomerID=?", (pk,)).fetchone()
    conn.close()
    return dict(row) if row else None


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        "SELECT CustomerID, CompanyName, ContactName, City, Country, Phone "
        "FROM Customers "
        "WHERE CustomerID LIKE ? OR CompanyName LIKE ? OR ContactName LIKE ? "
        "   OR City LIKE ? OR Country LIKE ? "
        "ORDER BY CompanyName",
        (like, like, like, like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def insert(cid: str, data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO Customers (CustomerID, CompanyName, ContactName, ContactTitle, "
        "Address, City, Region, PostalCode, Country, Phone, Fax) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            cid,
            data.get("CompanyName"),
            data.get("ContactName") or None,
            data.get("ContactTitle") or None,
            data.get("Address") or None,
            data.get("City") or None,
            data.get("Region") or None,
            data.get("PostalCode") or None,
            data.get("Country") or None,
            data.get("Phone") or None,
            data.get("Fax") or None,
        ),
    )
    conn.commit()
    conn.close()


def update(pk, data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE Customers SET CompanyName=?, ContactName=?, ContactTitle=?, "
        "Address=?, City=?, Region=?, PostalCode=?, Country=?, Phone=?, Fax=? "
        "WHERE CustomerID=?",
        (
            data.get("CompanyName"),
            data.get("ContactName") or None,
            data.get("ContactTitle") or None,
            data.get("Address") or None,
            data.get("City") or None,
            data.get("Region") or None,
            data.get("PostalCode") or None,
            data.get("Country") or None,
            data.get("Phone") or None,
            data.get("Fax") or None,
            pk,
        ),
    )
    conn.commit()
    conn.close()


def delete(pk) -> None:
    from data.delete_guards import can_delete_customer
    ok, reasons = can_delete_customer(pk)
    if not ok:
        raise ValueError("Cannot delete: " + "; ".join(reasons))
    conn = get_connection()
    conn.execute("DELETE FROM Customers WHERE CustomerID=?", (pk,))
    conn.commit()
    conn.close()
