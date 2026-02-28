# Northwind Traders TUI

A terminal-based warehouse/distribution management application built on the classic
**Northwind** sample database. Stack: **Python + Textual + SQLite**.

---

## Version History

| Version | Theme | Key additions |
|---------|-------|---------------|
| **v1.4** | Foundation | 9 CRUD panels, SQL editor, 6 reports + CSV export, PIN login, role-based UI, multi-column form modals |
| **v2.0** | Documents & Finance | Document workflow (WZ/FV/PZ/PW/RW), Cash Register & Bank Account, Charts, extended KPIs, 7 UX enhancements, finance dashboard KPIs |
| **v2.1** | PDF Export | Branded A4 PDF delivery notes (WZ) & invoices (FV) — company logo, theme colours, totals, linked WZ references |
| **v2.2** | PDF All Docs + UX | PDF export for PZ, KP, KW & Bank entries; Business Details tabbed layout with docked Save button |
| **v2.3** | UI Polish | Business Details compact one-screen tabs; form layout optimisation across Company / Tax / Documents |
| **v2.4** | Data Integrity | 3-tier roles (user/manager/admin), delete guards, document cancellation, Credit Notes (FK), 82 automated tests |
| ... | ... | ... |

---

## Features (v2.4)

### New in v2.4 — Data Integrity, Cancellation & Credit Notes

**3-Tier Role System**
- Hierarchical permissions: **user** (view + create) → **manager** (+ delete) → **admin** (+ cancel, FK, system)
- Delete buttons hidden from users without manager+ role
- Admin sections (SQL, Users, Business Details, Settings) remain admin-only

**Delete Guards**
- Referential integrity enforcement across all document and master data types
- Cannot delete an Order if WZ exists, cannot delete FV if payments exist, etc.
- Side-effects on delete: deleting a KP/BankEntry decrements FV.PaidAmount; deleting PW/RW reverses stock
- Human-readable error messages: *"Cannot delete: WZ WZ/2026/003 exists for this order"*

**Document Cancellation**
- Admin-only soft cancel for WZ, FV, and PZ — keeps full audit trail (CancelledAt, CancelledBy, CancelReason)
- **Cancel WZ** — reverses stock, blocks if invoiced (*"Cancel the FV first"*)
- **Cancel FV** — reverts linked WZ to "issued", blocks if payments exist (*"Issue FK instead"*)
- **Cancel PZ** — reverses stock, leaves linked payments for manual handling
- Cancellation reason modal with mandatory input; cancelled documents show reason in detail view

**Credit Notes (FK — Faktura Korygujaca)**
- Full invoice correction system following Polish accounting model
- Three FK types: **Full Reversal**, **Partial Correction**, **Cancellation**
- Adjusts FV.TotalNet in-place; recalculates payment status (paid / partial / issued / cancelled)
- Optional stock reversal via "Return goods to stock" checkbox
- Creation wizard: pick FV → select type → edit line items (partial) → reason + date → preview → create
- Read-only detail view with original vs corrected values side-by-side
- FK PDF export with correction table, original FV reference, and prominent "ANULOWANIE" banner for cancellations
- FV detail modal shows linked FK documents and "Issue FK" button
- Navigation: Documents → FK — Credit Notes

**Test Suite (82 tests)**
- `test_delete_guards.py` — guard functions, side-effects, master data referential integrity
- `test_cancellation.py` — WZ/FV/PZ cancellation rules, cascade behaviour, error cases
- `test_fk.py` — FK creation (all 3 types), payment/stock/pricing effects, search, numbering

---

## Features (v2.2)

### New in v2.2 — PDF for All Documents + UX Fixes

- **PDF export extended to all document types:**
  - **PZ Goods Receipts** — "Receive From" supplier box, line items table with unit cost and total cost row
  - **KP Cash Receipts** — voucher with customer name, FV reference, prominent amount box, signature line
  - **KW Cash Payments** — voucher with supplier name, PZ reference, prominent amount box, signature line
  - **Bank Account Entries** — direction badge (green MONEY IN / red MONEY OUT), counterparty, FV/PZ references, amount box
- **Business Details panel reorganised into 3 tabs** — Company, Tax & Legal, Documents — prevents content overflow
- **Save button always visible** — docked to the bottom of the Business Details panel
- **Tab content scrollable** — long forms scroll within the tab rather than clipping off-screen

---

## Features (v2.1)

### New in v2.1 — PDF Export

- **PDF button on WZ Delivery Notes** — generates a branded A4 PDF saved to `~/Downloads/`
- **PDF button on FV Invoices** — generates a branded A4 PDF saved to `~/Downloads/`
- Both documents include:
  - Company logo (if set in Business Details), name, address, contact info
  - Document title, number and date in the configured theme colour (blue / green / monochrome)
  - Ship To / Bill To address box
  - Line items table with alternating row shading and themed header row
  - VAT number and Tax ID band (when configured)
  - Configurable footer text and page N / M numbering
- **FV invoice extras**: Payment Details box (due date, terms, bank account), colour-coded Outstanding amount (red if unpaid, green if settled), linked WZ reference list
- **WZ price toggle**: `doc_wz_show_prices = false` in Business Details hides Unit Price and Line Total columns
- All branding (logo, colours, titles, footer) controlled via the **Business Details** panel — no code changes needed

---

## Features (v2.0)

### Core (v1.4)
- **9 CRUD panels** — Customers, Orders, Products, Employees, Suppliers, Categories,
  Shippers, Regions, Reports
- **Dashboard** with 10 live KPI cards
- **SQL Query editor** — type any SQL, press `ctrl+r`, see results in a table
- **Reports** with CSV export (11 report types)
- **Configurable currency** — symbol and name saved to SQLite ($ → £ → € etc.)
- **PIN-based login** with 3-tier role management (admin / manager / user)
- **Role-based UI** — admin sees SQL Query, Users, Settings and Business Details panels; managers can delete documents; regular users view and create only
- **Compact multi-column form modals** — related fields shown side-by-side via CSS `1fr` columns

### New in v2.0 — Documents & Finance

#### Document Workflow
- **WZ — Delivery Notes** — create draft, add/remove line items, issue WZ (deducts stock)
- **FV — Invoices** — generate from WZ or standalone; track payment status
- **PZ — Goods Receipts** — record supplier deliveries, update stock on issue
- **PW/RW — Stock Movements** — internal stock adjustments (receipts and issues)

#### Finance
- **Cash Register** — KP income entries, KW expense entries with running balance
- **Bank Account** — bank statement entries with cross-referenced Cash Register transfers

#### Analytics
- **Charts panel** — 4 tab views rendered as ANSI ASCII art via `plotext`:
  - *Sales Trend* — line chart of monthly revenue (rolling 12 months)
  - *Category Mix* — horizontal bar chart of revenue % by product category
  - *Top Employees* — bar chart of orders per employee
  - *Cash & Bank Account* — combined cash-flow view
  - Press `R` to refresh charts
- **10 KPI dashboard cards** — Orders Today, Revenue MTD, Low Stock, Pending Orders,
  Avg Fulfil Days, This Month trend arrow (↑/↓) and delta %, Cash Register Balance, Bank Account Balance,
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
  <tr>
    <td align="center">
      <a href="screenshots/invoice_pdf.png"><img src="screenshots/invoice_pdf.png" width="260" alt="FV Invoice PDF"/></a><br/>
      <sub><b>FV Invoice — exported PDF (v2.1)</b></sub>
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
      <sub><b>Bank Account entries</b></sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <a href="screenshots/cash-in-receipt.png"><img src="screenshots/cash-in-receipt.png" width="260" alt="KP Cash Receipt PDF"/></a><br/>
      <sub><b>KP Cash Receipt — exported PDF (v2.2)</b></sub>
    </td>
    <td align="center">
      <a href="screenshots/bank-transfer-pdf.png"><img src="screenshots/bank-transfer-pdf.png" width="260" alt="Bank Entry PDF"/></a><br/>
      <sub><b>Bank Account Entry — exported PDF (v2.2)</b></sub>
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
  <tr>
    <td align="center">
      <a href="screenshots/business-details-settings.png"><img src="screenshots/business-details-settings.png" width="260" alt="Business Details"/></a><br/>
      <sub><b>Business Details — tabbed layout (v2.2)</b></sub>
    </td>
    <td align="center">
      <a href="screenshots/general-settings.png"><img src="screenshots/general-settings.png" width="260" alt="General Settings"/></a><br/>
      <sub><b>General Settings panel</b></sub>
    </td>
  </tr>
</table>

---

## Installation

```bash
# 1. Clone
git clone git@github.com:AmigoUK/northwind.git
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
| `fpdf2` | ≥ 2.7 | PDF generation — branded delivery notes & invoices (v2.1) |
| `python-barcode` | ≥ 0.15 | GS1-128 / EAN-13 barcodes in PDFs *(planned)* |
| `Pillow` | ≥ 10.0 | Company logo embedding in PDFs (v2.1) |

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
├── pdf_export.py       # PDF generation for all document types (v2.1–v2.4)
├── northwind.tcss      # Textual CSS (layout, modals, panels, charts)
├── requirements.txt    # Python dependencies
├── data/               # Data-access layer (pure SQL, no UI)
│   ├── settings.py     # AppSettings key-value store (currency, theme, business details)
│   ├── users.py        # AppUsers CRUD + PIN authentication + role hierarchy (v2.4)
│   ├── dashboard.py    # KPI aggregations + kpis_extended()
│   ├── reports.py      # 11 report queries (sales, stock, trend, overdue…)
│   ├── delete_guards.py # Centralized delete guards + side-effect handlers (v2.4)
│   ├── wz.py           # WZ document CRUD + issue + cancel workflow
│   ├── fv.py           # FV invoice CRUD + cancel
│   ├── fk.py           # FK credit note CRUD + business logic (v2.4)
│   ├── pz.py           # PZ goods receipt CRUD + cancel
│   ├── kassa.py        # Cash Register entries
│   ├── bank.py         # Bank Account entries
│   └── ...             # customers, orders, products, employees, …
├── screens/            # Textual Widget subclasses (one per section)
│   ├── login.py        # LoginScreen modal (PIN gate)
│   ├── dashboard.py    # Dashboard KPI cards + recent orders
│   ├── charts.py       # Charts panel — Sales Trend / Category Mix / Employees / Cash & Bank Account
│   ├── reports.py      # Reports panel with 11 report types + CSV export
│   ├── fk.py           # FK Credit Notes panel + creation wizard + detail modal (v2.4)
│   ├── modals.py       # Shared modals: ConfirmDelete, CancellationReason (v2.4)
│   ├── wz.py           # WZ Delivery Notes panel + modals + cancel button
│   ├── fv.py           # FV Invoices panel + modals + FK integration
│   ├── pz.py           # PZ Goods Receipts panel + modals + cancel button
│   └── ...             # sql, settings, business, users, kassa, bank, …
└── tests/              # Automated test suite (v2.4)
    ├── conftest.py     # Fresh temp DB per test
    ├── test_data.py    # Core business logic (19 tests)
    ├── test_delete_guards.py  # Delete guards + side-effects (26 tests)
    ├── test_cancellation.py   # WZ/FV/PZ cancellation (13 tests)
    └── test_fk.py             # Credit Notes — all 3 types (24 tests)
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
| `fpdf2` subclassing for custom footers and multi-column layouts | `pdf_export.py` |
| Embedding images and drawing shapes/lines with FPDF primitives | `pdf_export.py` |
| Reusable PDF helpers (`_draw_header`, `_draw_amount_box`, `_draw_signature_line`) shared across document types | `pdf_export.py` |
| Generating voucher-style single-entry PDFs (KP, KW, Bank) vs multi-line table PDFs (WZ, FV, PZ) | `pdf_export.py` |
| CSS selector specificity in Textual — type+class beats class alone; later rules win on equal specificity | `northwind.tcss` |
| `dock: bottom` to pin a widget (Save button) regardless of sibling content height | `northwind.tcss` |
| `overflow-y: auto` on `TabPane` to make long forms scrollable within a tab | `northwind.tcss` |
| `TabbedContent` inside a panel to split a long settings page into navigable tabs | `screens/business.py` |
| Grouping related fields into 2- and 3-column `form-row` layouts to reduce vertical height | `screens/business.py` |
| Merging redundant sections (Company Identity + Contact Details) into one compact block | `screens/business.py` |
| Balancing widget height (Select `height: 2`) vs readability to keep forms within one screen | `northwind.tcss` |
| Hierarchical RBAC — numeric role levels with `has_permission()` comparator | `data/users.py` |
| Centralized delete guards returning `(bool, list[str])` reason tuples | `data/delete_guards.py` |
| Side-effect handlers that run before DELETE — payment reversal, stock restoration | `data/delete_guards.py` |
| Document cancellation as a state-machine transition with audit fields (CancelledAt/By/Reason) | `data/wz.py`, `data/fv.py`, `data/pz.py` |
| Credit note (FK) pattern — recording original vs corrected values per line item | `data/fk.py` |
| In-place FV.TotalNet adjustment on FK creation + status recalculation | `data/fk.py` |
| Multi-step creation wizard in a single ModalScreen (pick FV → type → items → confirm) | `screens/fk.py` |
| `conn.execute()` vs `conn.executescript()` for reliable schema migration on existing databases | `db.py` |
| pytest fixtures with `tmp_path` for isolated per-test SQLite databases | `tests/conftest.py` |
| Testing cross-document effects: Order → WZ → FV → KP → FK → verify all balances | `tests/test_fk.py` |
