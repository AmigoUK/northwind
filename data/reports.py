"""data/reports.py — SQL-only aggregation queries."""
from db import get_connection


def sales_by_customer() -> tuple[list, list]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.CustomerID,
                  c.CompanyName,
                  COUNT(DISTINCT o.OrderID) AS Orders,
                  COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0) AS Revenue
           FROM Customers c
           LEFT JOIN Orders o ON c.CustomerID = o.CustomerID
           LEFT JOIN OrderDetails od ON o.OrderID = od.OrderID
           GROUP BY c.CustomerID, c.CompanyName
           ORDER BY Revenue DESC"""
    ).fetchall()
    conn.close()
    headers = [("ID", 6), ("Company Name", 30), ("Orders", 7), ("Revenue", 12)]
    data = [[r["CustomerID"], r["CompanyName"], r["Orders"], f"${r['Revenue']:.2f}"] for r in rows]
    return headers, data


def sales_by_product() -> tuple[list, list]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.ProductID, p.ProductName, c.CategoryName,
                  COALESCE(SUM(od.Quantity), 0) AS UnitsSold,
                  COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0) AS Revenue
           FROM Products p
           LEFT JOIN Categories c ON p.CategoryID = c.CategoryID
           LEFT JOIN OrderDetails od ON p.ProductID = od.ProductID
           GROUP BY p.ProductID, p.ProductName, c.CategoryName
           ORDER BY Revenue DESC"""
    ).fetchall()
    conn.close()
    headers = [("ID", 4), ("Product Name", 26), ("Category", 16), ("Units Sold", 10), ("Revenue", 12)]
    data = [[r["ProductID"], r["ProductName"], r["CategoryName"], r["UnitsSold"], f"${r['Revenue']:.2f}"] for r in rows]
    return headers, data


def sales_by_employee() -> tuple[list, list]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT e.EmployeeID,
                  e.LastName || ', ' || e.FirstName AS EmployeeName,
                  e.Title,
                  COUNT(DISTINCT o.OrderID) AS Orders,
                  COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0) AS Revenue
           FROM Employees e
           LEFT JOIN Orders o ON e.EmployeeID = o.EmployeeID
           LEFT JOIN OrderDetails od ON o.OrderID = od.OrderID
           GROUP BY e.EmployeeID, e.LastName, e.FirstName, e.Title
           ORDER BY Revenue DESC"""
    ).fetchall()
    conn.close()
    headers = [("ID", 4), ("Employee Name", 22), ("Title", 26), ("Orders", 7), ("Revenue", 12)]
    data = [[r["EmployeeID"], r["EmployeeName"], r["Title"], r["Orders"], f"${r['Revenue']:.2f}"] for r in rows]
    return headers, data


def top_10() -> tuple[list, list]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.ProductName, c.CategoryName,
                  COALESCE(SUM(od.Quantity), 0) AS UnitsSold,
                  COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0) AS Revenue
           FROM Products p
           LEFT JOIN Categories c ON p.CategoryID = c.CategoryID
           LEFT JOIN OrderDetails od ON p.ProductID = od.ProductID
           GROUP BY p.ProductID, p.ProductName, c.CategoryName
           ORDER BY Revenue DESC
           LIMIT 10"""
    ).fetchall()
    conn.close()
    headers = [("Rank", 5), ("Product Name", 26), ("Category", 16), ("Units Sold", 10), ("Revenue", 12)]
    data = [[i + 1, r["ProductName"], r["CategoryName"], r["UnitsSold"], f"${r['Revenue']:.2f}"] for i, r in enumerate(rows)]
    return headers, data


def low_stock_alert() -> tuple[list, list]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.ProductID, p.ProductName, c.CategoryName,
                  p.UnitsInStock, p.ReorderLevel, p.UnitsOnOrder
           FROM Products p
           LEFT JOIN Categories c ON p.CategoryID = c.CategoryID
           WHERE p.UnitsInStock <= p.ReorderLevel AND p.Discontinued = 0
           ORDER BY p.UnitsInStock ASC"""
    ).fetchall()
    conn.close()
    headers = [("ID", 4), ("Product Name", 26), ("Category", 16), ("In Stock", 9), ("Reorder Lvl", 11), ("On Order", 8)]
    data = [[r["ProductID"], r["ProductName"], r["CategoryName"], r["UnitsInStock"], r["ReorderLevel"], r["UnitsOnOrder"]] for r in rows]
    return headers, data


def orders_by_date_range(date_from: str, date_to: str) -> tuple[list, list]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT o.OrderID,
                  c.CompanyName AS Customer,
                  e.LastName || ', ' || e.FirstName AS Employee,
                  o.OrderDate, o.ShippedDate,
                  COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0) AS Total
           FROM Orders o
           LEFT JOIN Customers c ON o.CustomerID = c.CustomerID
           LEFT JOIN Employees e ON o.EmployeeID = e.EmployeeID
           LEFT JOIN OrderDetails od ON o.OrderID = od.OrderID
           WHERE o.OrderDate BETWEEN ? AND ?
           GROUP BY o.OrderID ORDER BY o.OrderDate""",
        (date_from, date_to),
    ).fetchall()
    conn.close()
    headers = [("ID", 6), ("Customer", 25), ("Employee", 20), ("Order Date", 12), ("Shipped", 12), ("Total", 10)]
    data = [[r["OrderID"], r["Customer"], r["Employee"], r["OrderDate"], r["ShippedDate"] or "(pending)", f"${r['Total']:.2f}"] for r in rows]
    return headers, data
