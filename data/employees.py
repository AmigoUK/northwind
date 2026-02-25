from __future__ import annotations
"""data/employees.py — SQL-only data access for Employees."""
from db import get_connection


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT e.EmployeeID,
                  e.LastName || ', ' || e.FirstName AS Name,
                  e.Title, e.City,
                  m.LastName || ', ' || m.FirstName AS Manager
           FROM Employees e
           LEFT JOIN Employees m ON e.ReportsTo = m.EmployeeID
           ORDER BY e.EmployeeID"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def fetch_for_picker() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT EmployeeID, LastName || ', ' || FirstName AS Name, Title "
        "FROM Employees ORDER BY EmployeeID"
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def fetch_with_hierarchy() -> list:
    """Return all employees as dicts, with ReportsTo field, for building org chart."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT EmployeeID, FirstName, LastName, Title, ReportsTo "
        "FROM Employees ORDER BY EmployeeID"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM Employees WHERE EmployeeID=?", (pk,)).fetchone()
    conn.close()
    return dict(row) if row else None


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        """SELECT e.EmployeeID,
                  e.LastName || ', ' || e.FirstName AS Name,
                  e.Title, e.City,
                  m.LastName || ', ' || m.FirstName AS Manager
           FROM Employees e
           LEFT JOIN Employees m ON e.ReportsTo=m.EmployeeID
           WHERE e.LastName LIKE ? OR e.FirstName LIKE ? OR e.Title LIKE ? OR e.City LIKE ?
           ORDER BY e.LastName""",
        (like, like, like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def insert(data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO Employees (LastName, FirstName, Title, TitleOfCourtesy, "
        "BirthDate, HireDate, Address, City, Region, PostalCode, Country, "
        "HomePhone, Extension, Notes, ReportsTo) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            data.get("LastName"),
            data.get("FirstName"),
            data.get("Title") or None,
            data.get("TitleOfCourtesy") or None,
            data.get("BirthDate") or None,
            data.get("HireDate") or None,
            data.get("Address") or None,
            data.get("City") or None,
            data.get("Region") or None,
            data.get("PostalCode") or None,
            data.get("Country") or None,
            data.get("HomePhone") or None,
            data.get("Extension") or None,
            data.get("Notes") or None,
            data.get("ReportsTo") or None,
        ),
    )
    conn.commit()
    conn.close()


def update(pk, data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE Employees SET LastName=?, FirstName=?, Title=?, TitleOfCourtesy=?, "
        "BirthDate=?, HireDate=?, Address=?, City=?, Region=?, PostalCode=?, Country=?, "
        "HomePhone=?, Extension=?, Notes=?, ReportsTo=? WHERE EmployeeID=?",
        (
            data.get("LastName"),
            data.get("FirstName"),
            data.get("Title") or None,
            data.get("TitleOfCourtesy") or None,
            data.get("BirthDate") or None,
            data.get("HireDate") or None,
            data.get("Address") or None,
            data.get("City") or None,
            data.get("Region") or None,
            data.get("PostalCode") or None,
            data.get("Country") or None,
            data.get("HomePhone") or None,
            data.get("Extension") or None,
            data.get("Notes") or None,
            data.get("ReportsTo") or None,
            pk,
        ),
    )
    conn.commit()
    conn.close()


def delete(pk) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM Employees WHERE EmployeeID=?", (pk,))
    conn.commit()
    conn.close()
