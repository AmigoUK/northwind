# Northwind Traders TUI

A terminal-based CRUD application for the classic **Northwind** sample database,
built with **Python + Textual + SQLite** as a university learning project.

---

## Features

- **9 CRUD panels** — Customers, Orders, Products, Employees, Suppliers, Categories,
  Shippers, Regions, Reports
- **Dashboard** with live KPIs (customers, orders, low-stock count, total revenue)
- **SQL Query editor** — type any SQL, press `ctrl+r`, see results in a table
- **Reports** with CSV export (sales by customer, product, employee, date range…)
- **Configurable currency** — symbol and name saved to SQLite ($ → £ → € etc.)
- **PIN-based login** with role management (admin / user)
- **Role-based UI** — admin sees SQL Query, Users, and Settings panels; regular users do not

---

## Screenshots

> Run `python3 app.py` and take screenshots with your terminal tool or
> `screencapture -i screenshots/<name>.png` on macOS.

Place screenshots in the `screenshots/` folder and embed them here:

```
![Login screen](screenshots/login.png)
![Dashboard](screenshots/dashboard.png)
![SQL Query panel](screenshots/sql.png)
![User management](screenshots/users.png)
```

---

## Installation

```bash
# 1. Clone
git clone <repo-url>
cd northwind

# 2. Install dependencies (requires Python 3.10+)
pip install -r requirements.txt

# 3. Run
python3 app.py
```

Default login: **username** `admin` / **PIN** `1234`

---

## Project Structure

```
northwind/
├── app.py              # Textual App entry point, login flow, sidebar
├── db.py               # SQLite schema DDL + seed data
├── northwind.tcss      # Textual CSS (layout, modals, panels)
├── data/               # Data-access layer (pure SQL, no UI)
│   ├── settings.py     # AppSettings key-value store (currency etc.)
│   ├── users.py        # AppUsers CRUD + PIN authentication
│   ├── dashboard.py    # KPI aggregations
│   ├── reports.py      # Report queries (sales, stock, date range)
│   └── ...             # customers, orders, products, employees, …
└── screens/            # Textual Widget subclasses (one per section)
    ├── login.py        # LoginScreen modal (PIN gate)
    ├── sql.py          # SQL Query panel
    ├── settings.py     # Settings panel
    ├── users.py        # User management panel
    ├── dashboard.py    # Dashboard KPI + recent orders
    └── ...             # customers, orders, products, employees, …
```

---

## What I Learned

| Concept | Where it appears |
|---------|-----------------|
| SQLite with `sqlite3` — CRUD, JOINs, aggregations, transactions | `db.py`, `data/*.py` |
| `cursor.description` to read column names dynamically | `screens/sql.py` |
| `INSERT OR REPLACE` as a key-value upsert | `data/settings.py` |
| `hashlib.sha256` for one-way PIN hashing | `data/users.py` |
| Textual `ModalScreen` + `dismiss()` callback pattern | `screens/login.py`, all form modals |
| Role-based UI (same app, different views per role) | `app.py` `_apply_role_visibility()` |
| Textual `ContentSwitcher` for single-page navigation | `app.py` |
| `TextArea` widget for multi-line code input | `screens/sql.py` |
| CSV export with Python's `csv` module | `screens/sql.py`, reports |
| MVC-style layered architecture (`data/` + `screens/`) | whole project |

---

## Key Bindings

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `N` | New record (in active panel) |
| `F` | Focus search box (in active panel) |
| `ctrl+r` | Run SQL query (SQL Query panel) |
| `X` | Export current results to CSV (SQL Query panel) |
| `R` | Refresh dashboard |
| `ESC` | Close modal / go back |
