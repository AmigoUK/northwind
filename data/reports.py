"""data/reports.py — SQL-only aggregation queries."""
from db import get_connection
from data.settings import get_currency_symbol
from datetime import date as _date


def sales_by_customer(date_from: str = "0001-01-01",
                       date_to:   str = "9999-12-31") -> tuple[list, list]:
    sym = get_currency_symbol()
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.CustomerID,
                  c.CompanyName,
                  COUNT(DISTINCT o.OrderID) AS Orders,
                  COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0) AS Revenue
           FROM Customers c
           LEFT JOIN Orders o ON c.CustomerID = o.CustomerID
                             AND o.OrderDate BETWEEN ? AND ?
           LEFT JOIN OrderDetails od ON o.OrderID = od.OrderID
           GROUP BY c.CustomerID, c.CompanyName
           ORDER BY Revenue DESC""",
        (date_from, date_to),
    ).fetchall()
    conn.close()
    headers = [("ID", 6), ("Company Name", 30), ("Orders", 7), ("Revenue", 12)]
    data = [[r["CustomerID"], r["CompanyName"], r["Orders"], f"{sym}{r['Revenue']:.2f}"] for r in rows]
    return headers, data


def sales_by_product(date_from: str = "0001-01-01",
                      date_to:   str = "9999-12-31") -> tuple[list, list]:
    sym = get_currency_symbol()
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.ProductID, p.ProductName, c.CategoryName,
                  COALESCE(SUM(od.Quantity), 0) AS UnitsSold,
                  COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0) AS Revenue
           FROM Products p
           LEFT JOIN Categories c ON p.CategoryID = c.CategoryID
           LEFT JOIN OrderDetails od ON p.ProductID = od.ProductID
           LEFT JOIN Orders o ON od.OrderID = o.OrderID
                             AND o.OrderDate BETWEEN ? AND ?
           GROUP BY p.ProductID, p.ProductName, c.CategoryName
           ORDER BY Revenue DESC""",
        (date_from, date_to),
    ).fetchall()
    conn.close()
    headers = [("ID", 4), ("Product Name", 26), ("Category", 16), ("Units Sold", 10), ("Revenue", 12)]
    data = [[r["ProductID"], r["ProductName"], r["CategoryName"], r["UnitsSold"], f"{sym}{r['Revenue']:.2f}"] for r in rows]
    return headers, data


def sales_by_employee(date_from: str = "0001-01-01",
                       date_to:   str = "9999-12-31") -> tuple[list, list]:
    sym = get_currency_symbol()
    conn = get_connection()
    rows = conn.execute(
        """SELECT e.EmployeeID,
                  e.LastName || ', ' || e.FirstName AS EmployeeName,
                  e.Title,
                  COUNT(DISTINCT o.OrderID) AS Orders,
                  COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0) AS Revenue
           FROM Employees e
           LEFT JOIN Orders o ON e.EmployeeID = o.EmployeeID
                             AND o.OrderDate BETWEEN ? AND ?
           LEFT JOIN OrderDetails od ON o.OrderID = od.OrderID
           GROUP BY e.EmployeeID, e.LastName, e.FirstName, e.Title
           ORDER BY Revenue DESC""",
        (date_from, date_to),
    ).fetchall()
    conn.close()
    headers = [("ID", 4), ("Employee Name", 22), ("Title", 26), ("Orders", 7), ("Revenue", 12)]
    data = [[r["EmployeeID"], r["EmployeeName"], r["Title"], r["Orders"], f"{sym}{r['Revenue']:.2f}"] for r in rows]
    return headers, data


def top_10(date_from: str = "0001-01-01",
           date_to:   str = "9999-12-31") -> tuple[list, list]:
    sym = get_currency_symbol()
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.ProductName, c.CategoryName,
                  COALESCE(SUM(od.Quantity), 0) AS UnitsSold,
                  COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0) AS Revenue
           FROM Products p
           LEFT JOIN Categories c ON p.CategoryID = c.CategoryID
           LEFT JOIN OrderDetails od ON p.ProductID = od.ProductID
           LEFT JOIN Orders o ON od.OrderID = o.OrderID
                             AND o.OrderDate BETWEEN ? AND ?
           GROUP BY p.ProductID, p.ProductName, c.CategoryName
           ORDER BY Revenue DESC
           LIMIT 10""",
        (date_from, date_to),
    ).fetchall()
    conn.close()
    headers = [("Rank", 5), ("Product Name", 26), ("Category", 16), ("Units Sold", 10), ("Revenue", 12)]
    data = [[i + 1, r["ProductName"], r["CategoryName"], r["UnitsSold"], f"{sym}{r['Revenue']:.2f}"] for i, r in enumerate(rows)]
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


def monthly_revenue_trend(date_from: str = "0001-01-01",
                           date_to:   str = "9999-12-31") -> tuple[list, list]:
    """Revenue and order count grouped by month for the given date range, ordered ASC."""
    sym = get_currency_symbol()
    conn = get_connection()
    rows = conn.execute(
        """SELECT strftime('%Y-%m', o.OrderDate) AS Month,
                  COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0) AS Revenue,
                  COUNT(DISTINCT o.OrderID) AS Orders
           FROM Orders o
           LEFT JOIN OrderDetails od ON o.OrderID = od.OrderID
           WHERE o.OrderDate IS NOT NULL
             AND o.OrderDate BETWEEN ? AND ?
           GROUP BY strftime('%Y-%m', o.OrderDate)
           ORDER BY Month ASC""",
        (date_from, date_to),
    ).fetchall()
    conn.close()
    headers = [("Month", 10), ("Revenue", 14), ("Orders", 7)]
    data = [[r["Month"], f"{sym}{r['Revenue']:.2f}", r["Orders"]] for r in rows]
    return headers, data


def chart_employees(date_from: str = "0001-01-01",
                    date_to:   str = "9999-12-31") -> tuple[list, list]:
    """Returns (last_names, order_counts) for the Top Employees bar chart."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT e.LastName,
                  COUNT(DISTINCT o.OrderID) AS Orders
           FROM Employees e
           LEFT JOIN Orders o ON e.EmployeeID = o.EmployeeID
             AND o.OrderDate BETWEEN ? AND ?
           GROUP BY e.EmployeeID, e.LastName
           ORDER BY Orders DESC""",
        (date_from, date_to),
    ).fetchall()
    conn.close()
    return [r["LastName"] for r in rows], [int(r["Orders"]) for r in rows]


def order_fulfilment_time(date_from: str = "0001-01-01",
                           date_to:   str = "9999-12-31") -> tuple[list, list]:
    """Average days from order to ship by employee."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT e.LastName || ', ' || e.FirstName AS Employee,
                  COUNT(o.OrderID) AS Shipped,
                  ROUND(AVG(julianday(o.ShippedDate) - julianday(o.OrderDate)), 1) AS AvgDays
           FROM Orders o
           JOIN Employees e ON o.EmployeeID = e.EmployeeID
           WHERE o.ShippedDate IS NOT NULL AND o.OrderDate IS NOT NULL
             AND o.OrderDate BETWEEN ? AND ?
           GROUP BY o.EmployeeID, e.LastName, e.FirstName
           ORDER BY AvgDays""",
        (date_from, date_to),
    ).fetchall()
    conn.close()
    headers = [("Employee", 28), ("Shipped Orders", 14), ("Avg Days", 8)]
    data = [[r["Employee"], r["Shipped"], r["AvgDays"]] for r in rows]
    return headers, data


def category_revenue(date_from: str = "0001-01-01",
                      date_to:   str = "9999-12-31") -> tuple[list, list]:
    """Revenue and units sold per product category."""
    sym = get_currency_symbol()
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.CategoryName,
                  COALESCE(SUM(od.Quantity), 0) AS Units,
                  COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0) AS Revenue
           FROM Categories c
           LEFT JOIN Products p ON c.CategoryID = p.CategoryID
           LEFT JOIN OrderDetails od ON p.ProductID = od.ProductID
           LEFT JOIN Orders o ON od.OrderID = o.OrderID
                             AND o.OrderDate BETWEEN ? AND ?
           GROUP BY c.CategoryID, c.CategoryName
           ORDER BY Revenue DESC""",
        (date_from, date_to),
    ).fetchall()
    conn.close()
    headers = [("Category", 22), ("Units Sold", 10), ("Revenue", 14)]
    data = [[r["CategoryName"], r["Units"], f"{sym}{r['Revenue']:.2f}"] for r in rows]
    return headers, data


def repeat_customers(date_from: str = "0001-01-01",
                      date_to:   str = "9999-12-31") -> tuple[list, list]:
    """Customers with more than one order and their lifetime value."""
    sym = get_currency_symbol()
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.CustomerID,
                  c.CompanyName,
                  COUNT(DISTINCT o.OrderID) AS Orders,
                  COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0) AS LTV
           FROM Customers c
           JOIN Orders o ON c.CustomerID = o.CustomerID
                        AND o.OrderDate BETWEEN ? AND ?
           LEFT JOIN OrderDetails od ON o.OrderID = od.OrderID
           GROUP BY c.CustomerID, c.CompanyName
           HAVING COUNT(DISTINCT o.OrderID) > 1
           ORDER BY LTV DESC""",
        (date_from, date_to),
    ).fetchall()
    conn.close()
    headers = [("ID", 6), ("Company Name", 30), ("Orders", 7), ("Lifetime Value", 14)]
    data = [[r["CustomerID"], r["CompanyName"], r["Orders"], f"{sym}{r['LTV']:.2f}"] for r in rows]
    return headers, data


def overdue_orders() -> tuple[list, list]:
    """Orders where ShippedDate is NULL and RequiredDate is in the past."""
    today = str(_date.today())
    conn = get_connection()
    rows = conn.execute(
        """SELECT o.OrderID,
                  COALESCE(c.CompanyName, o.CustomerID) AS Customer,
                  o.OrderDate,
                  o.RequiredDate
           FROM Orders o
           LEFT JOIN Customers c ON o.CustomerID = c.CustomerID
           WHERE o.ShippedDate IS NULL
             AND o.RequiredDate IS NOT NULL
             AND o.RequiredDate < ?
           ORDER BY o.RequiredDate""",
        (today,),
    ).fetchall()
    conn.close()
    headers = [("OrderID", 8), ("Customer", 28), ("Order Date", 12), ("Due Date", 12)]
    data = [[r["OrderID"], r["Customer"], r["OrderDate"] or "", r["RequiredDate"]] for r in rows]
    return headers, data


def orders_by_date_range(date_from: str = "0001-01-01",
                          date_to:   str = "9999-12-31") -> tuple[list, list]:
    sym = get_currency_symbol()
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
    data = [[r["OrderID"], r["Customer"], r["Employee"], r["OrderDate"], r["ShippedDate"] or "(pending)", f"{sym}{r['Total']:.2f}"] for r in rows]
    return headers, data
