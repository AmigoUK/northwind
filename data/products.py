from __future__ import annotations
"""data/products.py — SQL-only data access for Products."""
from db import get_connection


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.ProductID, p.ProductName, c.CategoryName, s.CompanyName AS Supplier,
                  p.UnitPrice, p.UnitsInStock, p.Discontinued
           FROM Products p
           LEFT JOIN Categories c ON p.CategoryID = c.CategoryID
           LEFT JOIN Suppliers  s ON p.SupplierID = s.SupplierID
           ORDER BY p.ProductID"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def fetch_for_picker() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.ProductID, p.ProductName, c.CategoryName, p.UnitPrice, p.UnitsInStock
           FROM Products p
           LEFT JOIN Categories c ON p.CategoryID=c.CategoryID
           WHERE p.Discontinued=0
           ORDER BY p.ProductID"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT p.*, c.CategoryName, s.CompanyName AS SupplierName
           FROM Products p
           LEFT JOIN Categories c ON p.CategoryID=c.CategoryID
           LEFT JOIN Suppliers  s ON p.SupplierID=s.SupplierID
           WHERE p.ProductID=?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.ProductID, p.ProductName, c.CategoryName, s.CompanyName,
                  p.UnitPrice, p.UnitsInStock, p.Discontinued
           FROM Products p
           LEFT JOIN Categories c ON p.CategoryID=c.CategoryID
           LEFT JOIN Suppliers  s ON p.SupplierID=s.SupplierID
           WHERE p.ProductName LIKE ? OR c.CategoryName LIKE ? OR s.CompanyName LIKE ?
           ORDER BY p.ProductName""",
        (like, like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def low_stock() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.ProductID, p.ProductName, c.CategoryName, s.CompanyName AS Supplier,
                  p.UnitPrice, p.UnitsInStock, p.Discontinued
           FROM Products p
           LEFT JOIN Categories c ON p.CategoryID = c.CategoryID
           LEFT JOIN Suppliers  s ON p.SupplierID = s.SupplierID
           WHERE p.UnitsInStock <= p.ReorderLevel AND p.Discontinued = 0
           ORDER BY p.UnitsInStock"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def insert(data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO Products (ProductName, SupplierID, CategoryID, QuantityPerUnit, "
        "UnitPrice, UnitsInStock, UnitsOnOrder, ReorderLevel, Discontinued) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            data.get("ProductName"),
            data.get("SupplierID") or None,
            data.get("CategoryID") or None,
            data.get("QuantityPerUnit") or None,
            data.get("UnitPrice", 0.0),
            data.get("UnitsInStock", 0),
            data.get("UnitsOnOrder", 0),
            data.get("ReorderLevel", 0),
            1 if data.get("Discontinued") else 0,
        ),
    )
    conn.commit()
    conn.close()


def update(pk, data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE Products SET ProductName=?, SupplierID=?, CategoryID=?, QuantityPerUnit=?, "
        "UnitPrice=?, UnitsInStock=?, UnitsOnOrder=?, ReorderLevel=?, Discontinued=? "
        "WHERE ProductID=?",
        (
            data.get("ProductName"),
            data.get("SupplierID") or None,
            data.get("CategoryID") or None,
            data.get("QuantityPerUnit") or None,
            data.get("UnitPrice", 0.0),
            data.get("UnitsInStock", 0),
            data.get("UnitsOnOrder", 0),
            data.get("ReorderLevel", 0),
            1 if data.get("Discontinued") else 0,
            pk,
        ),
    )
    conn.commit()
    conn.close()


def apply_stock_delta(product_id: int, delta: int, conn) -> None:
    """Atomically adjust UnitsInStock by delta within caller's transaction. No commit."""
    conn.execute(
        "UPDATE Products SET UnitsInStock = UnitsInStock + ? WHERE ProductID = ?",
        (delta, product_id),
    )


def delete(pk) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM Products WHERE ProductID=?", (pk,))
    conn.commit()
    conn.close()
