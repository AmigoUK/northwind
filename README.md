# Northwind Traders TUI

A terminal-based warehouse/distribution management application built on the classic
**Northwind** sample database. Stack: **Python + Textual + SQLite**.

---

## Version History

| Version | Theme | Key additions |
|---------|-------|---------------|
| **v1.4** | Foundation | 9 CRUD panels, SQL editor, 6 reports + CSV export, PIN login, role-based UI, multi-column form modals |
| **v2.0** | Documents & Finance | Document workflow (WZ/FV/PZ/PW/RW), Cash Register & Bank, Charts, extended KPIs, 7 UX enhancements, finance dashboard KPIs |
| v2.1 | PDF Export | PDF delivery notes & invoices, company branding *(planned)* |
| ... | ... | ... |

---

## Features (v2.0)

### Core (v1.4)
- **9 CRUD panels** — Customers, Orders, Products, Employees, Suppliers, Categories,
  Shippers, Regions, Reports
- **Dashboard** with 10 live KPI cards
- **SQL Query editor** — type any SQL, press `ctrl+r`, see results in a table
- **Reports** with CSV export (11 report types)
- **Configurable currency** — symbol and name saved to SQLite ($ → £ → € etc.)
- **PIN-based login** with role management (admin / user)
- **Role-based UI** — admin sees SQL Query, Users, Settings and Business Details panels; regular users do not
- **Compact multi-column form modals** — related fields shown side-by-side via CSS `1fr` columns

### New in v2.0 — Documents & Finance

#### Document Workflow
- **WZ — Delivery Notes** — create draft, add/remove line items, issue WZ (deducts stock)
- **FV — Invoices** — generate from WZ or standalone; track payment status
- **PZ — Goods Receipts** — record supplier deliveries, update stock on issue
- **PW/RW — Stock Movements** — internal stock adjustments (receipts and issues)

#### Finance
- **Cash Register** — KP income entries, KW expense entries with running balance
- **Bank** — bank statement entries with cross-referenced Cash Register transfers

#### Analytics
- **Charts panel** — 4 tab views rendered as ANSI ASCII art via `plotext`:
  - *Sales Trend* — line chart of monthly revenue (rolling 12 months)
  - *Category Mix* — horizontal bar chart of revenue % by product category
  - *Top Employees* — bar chart of orders per employee
  - *Cash & Bank* — combined cash-flow view
  - Press `R` to refresh charts
- **10 KPI dashboard cards** — Orders Today, Revenue MTD, Low Stock, Pending Orders,
  Avg Fulfil Days, This Month trend arrow (↑/↓) and delta %, Cash Register Balance, Bank Balance,
  Open Invoices, Open WZ
- **11 report types** in the Reports dropdown with date-range filter and CSV export

---

## Screenshots

> Click any thumbnail to view full size.

### Dashboard & Analytics

<table>
  <tr>
    <td align="center">
      <a href="screenshots/dashboard.png"><img src="screenshots/dashboard.png" width="260" alt="Dashboard"/></a><br/>
      <sub><b>Dashboard (10 KPI cards + recent orders)</b></sub>
    </td>
    <td align="center">
      <a href="screenshots/charts.png"><img src="screenshots/charts.png" width="260" alt="Charts"/></a><br/>
      <sub><b>Charts (Sales Trend sparkline + period selector)</b></sub>
    </td>
    <td align="center">
      <a href="screenshots/reports-lv.png"><img src="screenshots/reports-lv.png" width="260" alt="Reports"/></a><br/>
      <sub><b>Reports (11 report types + date range filter)</b></sub>
    </td>
  </tr>
</table>

### Master Data

<table>
  <tr>
    <td align="center">
      <a href="screenshots/customers-lv.png"><img src="screenshots/customers-lv.png" width="260" alt="Customers list"/></a><br/>
      <sub><b>Customers list view</b></sub>
    </td>
    <td align="center">
      <a href="screenshots/customers-dv.png"><img src="screenshots/customers-dv.png" width="260" alt="Customer detail"/></a><br/>
      <sub><b>Customer detail modal</b></sub>
    </td>
    <td align="center">
      <a href="screenshots/products-lv.png"><img src="screenshots/products-lv.png" width="260" alt="Products"/></a><br/>
      <sub><b>Products list (Low Stock toggle)</b></sub>
    </td>
  </tr>
</table>

### Document Workflow

<table>
  <tr>
    <td align="center">
      <a href="screenshots/wz-dv.png"><img src="screenshots/wz-dv.png" width="260" alt="WZ Delivery Note"/></a><br/>
      <sub><b>WZ Delivery Note detail</b></sub>
    </td>
    <td align="center">
      <a href="screenshots/inv-dv-from-delivery-notes.png"><img src="screenshots/inv-dv-from-delivery-notes.png" width="260" alt="FV Invoice"/></a><br/>
      <sub><b>FV Invoice (generated from delivery note)</b></sub>
    </td>
    <td align="center">
      <a href="screenshots/odrers-dv.png"><img src="screenshots/odrers-dv.png" width="260" alt="Order detail"/></a><br/>
      <sub><b>Order detail view</b></sub>
    </td>
  </tr>
</table>

### Finance & Admin

<table>
  <tr>
    <td align="center">
      <a href="screenshots/cash-lv.png"><img src="screenshots/cash-lv.png" width="260" alt="Kasa"/></a><br/>
      <sub><b>Cash Register with KP/KW tabs</b></sub>
    </td>
    <td align="center">
      <a href="screenshots/bank-lv.png"><img src="screenshots/bank-lv.png" width="260" alt="Bank"/></a><br/>
      <sub><b>Bank entries</b></sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <a href="screenshots/sql-query.png"><img src="screenshots/sql-query.png" width="260" alt="SQL Query"/></a><br/>
      <sub><b>SQL Query editor</b></sub>
    </td>
    <td align="center">
      <a href="screenshots/themes.png"><img src="screenshots/themes.png" width="260" alt="Theme picker"/></a><br/>
      <sub><b>Theme picker</b></sub>
    </td>
  </tr>
</table>

---

## Installation

```bash
# 1. Clone
git clone <repo-url>
cd northwind

# 2. Install dependencies (Python 3.10+)
pip install -r requirements.txt

# 3. (macOS) Ensure pip-installed scripts are on PATH
#    Add to ~/.zshrc or ~/.bashrc:
export PATH="$PATH:$(python3 -m site --user-base)/bin"

# 4. Run
python3 app.py
```

Default login: **username** `admin` / **PIN** `1234`

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `textual` | ≥ 0.80.0 | TUI framework |
| `plotext` | ≥ 5.2 | ASCII charts in terminal (v2.0) |
| `fpdf2` | ≥ 2.7 | PDF generation — delivery notes & invoices *(v2.1)* |
| `python-barcode` | ≥ 0.15 | GS1-128 / EAN-13 barcodes in PDFs *(v2.2)* |
| `Pillow` | ≥ 10.0 | PNG barcode image rendering *(v2.2)* |

Install all at once:
```bash
pip install -r requirements.txt
```

---

## Project Structure

```
northwind/
├── app.py              # Textual App entry point, login flow, sidebar nav
├── db.py               # SQLite schema DDL + seed data
├── northwind.tcss      # Textual CSS (layout, modals, panels, charts)
├── requirements.txt    # Python dependencies
├── data/               # Data-access layer (pure SQL, no UI)
│   ├── settings.py     # AppSettings key-value store (currency, theme, business details)
│   ├── users.py        # AppUsers CRUD + PIN authentication
│   ├── dashboard.py    # KPI aggregations + kpis_extended()
│   ├── reports.py      # 11 report queries (sales, stock, trend, overdue…)
│   ├── wz.py           # WZ document CRUD + issue workflow
│   ├── fv.py           # FV invoice CRUD
│   ├── pz.py           # PZ goods receipt CRUD
│   ├── kassa.py        # Cash Register entries
│   ├── bank.py         # Bank entries
│   └── ...             # customers, orders, products, employees, …
└── screens/            # Textual Widget subclasses (one per section)
    ├── login.py        # LoginScreen modal (PIN gate)
    ├── dashboard.py    # Dashboard KPI cards + recent orders
    ├── charts.py       # Charts panel — Sales Trend / Category Mix / Employees / Cash & Bank
    ├── reports.py      # Reports panel with 11 report types + CSV export
    ├── sql.py          # SQL Query panel
    ├── settings.py     # Settings panel (currency, theme, stock control)
    ├── business.py     # Business Details panel (company info, doc defaults)
    ├── users.py        # User management panel
    ├── wz.py           # WZ Delivery Notes panel + modals
    ├── fv.py           # FV Invoices panel + modals
    ├── pz.py           # PZ Goods Receipts panel + modals
    ├── kassa.py        # Cash Register panel
    ├── bank.py         # Bank entries panel
    └── ...             # customers, orders, products, employees, …
```

---

## Key Bindings

| Key | Action |
|-----|--------|
| `ctrl+Q` | Quit (shows confirmation dialog) |
| `N` | New record (in active panel) |
| `F` | Focus search box (in active panel) |
| `ctrl+r` | Run SQL query (SQL Query panel) |
| `X` | Export current view to CSV |
| `R` | Refresh (Dashboard / Charts / Reports) |
| `ESC` | Close modal / go back |

---

## What I Learned

| Concept | Where it appears |
|---------|-----------------|
| SQLite with `sqlite3` — CRUD, JOINs, aggregations, transactions | `db.py`, `data/*.py` |
| `cursor.description` to read column names dynamically | `screens/sql.py` |
| `INSERT OR REPLACE` as a key-value upsert | `data/settings.py` |
| `hashlib.sha256` for one-way PIN hashing | `data/users.py` |
| Textual `ModalScreen` + `dismiss()` callback pattern | all form modals |
| Role-based UI (same app, different views per role) | `app.py` `_apply_role_visibility()` |
| Textual `ContentSwitcher` for single-page navigation | `app.py` |
| `TextArea` widget for multi-line code input | `screens/sql.py` |
| CSV export with Python's `csv` module | `screens/sql.py`, reports |
| MVC-style layered architecture (`data/` + `screens/`) | whole project |
| CSS `1fr` columns for multi-column form rows | `northwind.tcss`, all form modals |
| `plotext` for ANSI ASCII charts inside Textual `Static` widgets | `screens/charts.py` |
| `TabbedContent` + `TabPane` for multi-view panels | `screens/charts.py`, regions |
| SQL window functions: `strftime`, `julianday`, `AVG` | `data/reports.py`, `data/dashboard.py` |
| Document workflow state machine (draft → issued) | `data/wz.py`, `data/fv.py`, `data/pz.py` |
| Key-value settings store for business/document config | `data/settings.py`, `screens/business.py` |
