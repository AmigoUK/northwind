from __future__ import annotations
"""data/products.py — SQL-only data access for Products."""
from db import get_connection


def fetch_all() -> list:
    from data.settings import get_setting
    hide = get_setting("show_discontinued", "false").lower() != "true"
    where = "WHERE p.Discontinued = 0" if hide else ""
    conn = get_connection()
    rows = conn.execute(
        f"""SELECT p.ProductID, p.ProductName, c.CategoryName, s.CompanyName AS Supplier,
                  p.UnitPrice, p.UnitsInStock, p.Discontinued
           FROM Products p
           LEFT JOIN Categories c ON p.CategoryID = c.CategoryID
           LEFT JOIN Suppliers  s ON p.SupplierID = s.SupplierID
           {where}
           ORDER BY p.ProductID"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def fetch_all_full() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.ProductID, p.ProductName,
                  p.SupplierID, s.CompanyName AS SupplierName,
                  p.CategoryID, c.CategoryName,
                  p.QuantityPerUnit, p.UnitPrice,
                  p.UnitsInStock, p.UnitsOnOrder,
                  p.ReorderLevel, p.Discontinued
           FROM Products p
           LEFT JOIN Categories c ON p.CategoryID = c.CategoryID
           LEFT JOIN Suppliers  s ON p.SupplierID = s.SupplierID
           ORDER BY p.ProductID"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


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
    from data.settings import get_setting
    hide = get_setting("show_discontinued", "false").lower() != "true"
    disc_clause = "AND p.Discontinued = 0" if hide else ""
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        f"""SELECT p.ProductID, p.ProductName, c.CategoryName, s.CompanyName,
                  p.UnitPrice, p.UnitsInStock, p.Discontinued
           FROM Products p
           LEFT JOIN Categories c ON p.CategoryID=c.CategoryID
           LEFT JOIN Suppliers  s ON p.SupplierID=s.SupplierID
           WHERE (p.ProductName LIKE ? OR c.CategoryName LIKE ? OR s.CompanyName LIKE ?)
             {disc_clause}
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


def get_stock(product_id: int, conn=None) -> int:
    """Return current UnitsInStock for a product. Opens its own connection if conn is None."""
    close = conn is None
    if conn is None:
        conn = get_connection()
    row = conn.execute(
        "SELECT UnitsInStock FROM Products WHERE ProductID=?", (product_id,)
    ).fetchone()
    if close:
        conn.close()
    return row[0] if row else 0


def apply_stock_delta(product_id: int, delta: int, conn) -> None:
    """Atomically adjust UnitsInStock by delta within caller's transaction. No commit."""
    conn.execute(
        "UPDATE Products SET UnitsInStock = UnitsInStock + ? WHERE ProductID = ?",
        (delta, product_id),
    )


def delete(pk) -> None:
    from data.delete_guards import can_delete_product
    ok, reasons = can_delete_product(pk)
    if not ok:
        raise ValueError("Cannot delete: " + "; ".join(reasons))
    conn = get_connection()
    conn.execute("DELETE FROM Products WHERE ProductID=?", (pk,))
    conn.commit()
    conn.close()
