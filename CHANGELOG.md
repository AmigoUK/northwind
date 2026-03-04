# Northwind Traders — Changelog

Full release notes for each version. See [README](README.md) for installation, screenshots,
and key bindings.

---

## Features (v2.18)

### New in v2.18 — Backup on Quit

- **Three-button quit dialog** — `Ctrl+Q` now shows **Cancel**, **Quit**, and **Backup & Quit** instead of the previous Yes/No
- **Timestamped backup** — "Backup & Quit" copies `northwind.db` → `northwind_backup_YYYY-MM-DD_HH-MM-SS.db` in the working directory before exiting
- **Toast notification** — a brief on-screen notification shows the backup filename on success, or an error message if the copy fails
- **Safe-cancel default** — Cancel button receives focus by default; pressing Esc always cancels without quitting
- **Keyboard shortcuts in the dialog** — `Esc` = cancel, `Q` = quit without backup, `B` = backup & quit

---

## Features (v2.17)

### New in v2.17 — Cash Register Integrity

- **Non-negative balance enforced** — `create_cp()` and `transfer_to_bank()` in `data/cash.py` now raise `ValueError` if the requested amount exceeds the current cash register balance; the UI surfaces this as an error notification and refuses the operation
- **`get_cash_balance()` helper** — single source of truth in `data/cash.py` that returns CR total minus CP total; used by both guards and by the GR fallback
- **GR cash-payment fallback** — when receiving a GR with `payment_method="cash"`, `data/gr.py` checks the balance first and silently switches to a bank payment if cash is insufficient; no crash, no negative register
- **Demo data stays ≥ $0** — `_generate_transfer()` in `data/demo.py` skips the monthly cash sweep when the register is empty and clamps the sweep amount to the available balance; demo generation (Settings → Insert Demo Data) now always produces a non-negative cash register throughout the full 13-month history
- **Cash & Bank report** — the Cash & Bank Account Status chart will no longer show a –$78 k dip after inserting demo data

---

## Features (v2.16)

### New in v2.16 — Demo Data Test/Production Switch + Clean Database

- **Test/Production mode switch** — Settings › Demo Data gains a `Switch` widget that shows the current database mode; label reads "Test Mode" or "Production"
- **Toggle Production → Test** — opens `TestModeWarningModal`: red bold warning that ~1 500 records will be added, PIN-protected, max 3 attempts; cancel reverts the switch
- **Toggle Test → Production** — opens the existing `CleanDatabaseModal` with updated body text; cancel reverts the switch
- **"Clean Database" button** (renamed from "Clean Demo Data") — same PIN modal, same behaviour; modal text now explicitly lists what is preserved: settings, business details, and user accounts
- **`.modal-warning` CSS class** — red bold label style used in both modals for destructive-action summaries
- **Async Switch.Changed fix** — `Switch.value` enqueues a message rather than firing synchronously; the handler guards against re-entrant modal launches by comparing the incoming value against the persisted DB state

---

## Features (v2.15)

### New in v2.15 — Help System Overhaul

- **Searchable Help panel** — full-text filter across all topics; sidebar table of contents with category column
- **FAQ category** — curated answers to the most common workflow questions (how to invoice, cancel a DN, record a payment, etc.)
- **All stale topics updated** — topics that referenced old Polish abbreviations (WZ, FV…) or missing features now reflect the current v2.14+ state
- **Context-sensitive `?` shortcut** — pressing `?` from any panel switches to Help and pre-filters to the topic most relevant to that panel (e.g. `?` from Invoices → "Invoices" topic); second press with no filter shows all topics

---

## Features (v2.14)

### New in v2.14 — QR Codes on All PDF Documents

- **QR code in every PDF header** — all 7 document types (DN, INV, GR, CR, CP, Bank, CN) embed a scannable 20 mm QR code flush with the top-right corner of the branded header
- **Pipe-delimited payload** — each QR encodes doc type, number, date, counterparty name and key financial fields (e.g. `INV|INV/2026/001|2026-03-03|Acme Corp|1250.00|0.00|bank transfer`)
- **Toggle in Business Details → Documents tab** — "Show QR codes on all documents" switch; on by default (fresh DB with no saved setting shows QR)
- **Safe by design** — QR generation wrapped in `try/except`; any failure is silently skipped so PDF export always succeeds
- **Supplier Spending report** — new report type (now 12 total); shows GR totals per supplier with date-range filter
- **Company logo browser** — Business Details → Company tab has a Browse button; selected image is copied to `assets/logo<ext>` inside the app folder
- **Sales report JOIN fix** — `sales_by_customer` and `sales_by_product` now use inner JOIN so customers/products with no orders in the selected period are excluded

---

## Features (v2.13)

### New in v2.13 — AR/AP All Unpaid View

- **All Unpaid default view** — Reconciliation panel opens immediately showing all outstanding invoices (AR) or unallocated goods receipts (AP) — no entity pick required
- **Sub-view toggle** — `[All Unpaid]` / `[Statement]` buttons (keyboard `U` / `S`) switch between the flat unpaid list and the per-entity running-balance ledger
- **Optional filter** — `▼ Filter` button narrows the unpaid list to one customer/supplier; `✕ Clear` resets to all entities
- **Pay Invoice from unpaid list** — select any INV row in the unpaid view and press `P` to register a payment directly
- **AR Aging bar** — visible in the All Unpaid AR view
- **4 new automated tests** — `fetch_all_unpaid_inv` and `fetch_all_unpaid_gr` (all + filtered)

---

## Features (v2.10)

### New in v2.10 — Import/Export Fixes

- **Ctrl+X / Ctrl+I keybindings** — export and import bindings now work correctly from any active panel
- **Products CSV import fix** — column aliases corrected so exported Product CSVs re-import without errors
- **Orders CSV import fix** — column aliases corrected so exported Order CSVs re-import without errors

---

## Features (v2.9)

### New in v2.9 — CSV Round-Trip Fix

CSV import now accepts the short display headers used by CSV export (e.g. `ID`, `Company`, `Contact`) in addition to the original database column names (`CustomerID`, `CompanyName`, `ContactName`). This means you can export a table with Ctrl+X, clean the database, and re-import the same CSV with Ctrl+I without errors.

- Added `_ALIASES` mapping in `data/csv_import.py` covering all 4 importable tables (Customers, Suppliers, Products, Categories)
- Aliases are merged into the header normalization map using `setdefault` so exact DB column matches always take priority
- 145 automated tests pass (including all 15 CSV import tests)

---

## Features (v2.8)

### New in v2.8 — File Selector & Export Cleanup

**File Browser Modal (`FileSelectModal`)**
- Reusable file browser with `DirectoryTree` navigation, rooted at home directory
- Two modes: **save** (CSV/PDF export — pick save location) and **open** (CSV import — pick existing file)
- Pre-filled suggested filename for exports; extension filter hides irrelevant files in the tree
- Clicking a directory updates the path; clicking a file selects it; validates before accepting

**CSV Export Centralized**
- All 10 CSV export screens now use a shared `export_csv_with_selector()` helper
- Each `action_export_csv()` reduced from ~12 lines to ~4 lines
- File selector modal opens on export — user chooses save location instead of hardcoded `~/Downloads/`

**PDF Export with Save Location**
- All 7 PDF export functions (`export_dn`, `export_inv`, `export_gr`, `export_cr`, `export_cp`, `export_bank_entry`, `export_cn`) accept optional `save_path` parameter
- `export_dn` and `export_inv` refactored to use shared `_save_pdf()` helper (eliminated inline save duplication)
- All 7 PDF screen handlers wrapped with `FileSelectModal` for user-chosen save location

**CSV Import Browse Button**
- `ImportCSVModal` gains a **Browse...** button that opens `FileSelectModal(mode="open", file_filter=".csv")`
- Selected path fills the existing file path Input; manual typing still works

---

## Features (v2.5)

### New in v2.5 — English International

All Polish accounting abbreviations replaced with English equivalents across the entire codebase:

| Old (Polish) | New (English) | Full Name |
|-------------|---------------|-----------|
| WZ | DN | Delivery Note |
| FV | INV | Invoice |
| FK | CN | Credit Note |
| PZ | GR | Goods Receipt |
| PW | SI | Stock Issue |
| RW | SO | Stock Out |
| KP | CR | Cash Receipt |
| KW | CP | Cash Payment |

Database migration is automatic — existing databases are migrated on startup.

---

## Features (v2.4)

### New in v2.4 — Data Integrity, Cancellation & Credit Notes

**3-Tier Role System**
- Hierarchical permissions: **user** (view + create) → **manager** (+ delete) → **admin** (+ cancel, CN, system)
- Delete buttons hidden from users without manager+ role
- Admin sections (SQL, Users, Business Details, Settings) remain admin-only

**Delete Guards**
- Referential integrity enforcement across all document and master data types
- Cannot delete an Order if DN exists, cannot delete INV if payments exist, etc.
- Side-effects on delete: deleting a CR/BankEntry decrements INV.PaidAmount; deleting SI/SO reverses stock
- Human-readable error messages: *"Cannot delete: DN DN/2026/003 exists for this order"*

**Document Cancellation**
- Admin-only soft cancel for DN, INV, and GR — keeps full audit trail (CancelledAt, CancelledBy, CancelReason)
- **Cancel DN** — reverses stock, blocks if invoiced (*"Cancel the INV first"*)
- **Cancel INV** — reverts linked DN to "issued", blocks if payments exist (*"Issue CN instead"*)
- **Cancel GR** — reverses stock, leaves linked payments for manual handling
- Cancellation reason modal with mandatory input; cancelled documents show reason in detail view

**Credit Notes (CN)**
- Full invoice correction system
- Three CN types: **Full Reversal**, **Partial Correction**, **Cancellation**
- Adjusts INV.TotalNet in-place; recalculates payment status (paid / partial / issued / cancelled)
- Optional stock reversal via "Return goods to stock" checkbox
- Creation wizard: pick INV → select type → edit line items (partial) → reason + date → preview → create
- Read-only detail view with original vs corrected values side-by-side
- CN PDF export with correction table, original INV reference, and prominent "CANCELLATION" banner for cancellations
- INV detail modal shows linked CN documents and "Issue CN" button
- Navigation: Documents → CN — Credit Notes

**Test Suite (82 tests)**
- `test_delete_guards.py` — guard functions, side-effects, master data referential integrity
- `test_cancellation.py` — DN/INV/GR cancellation rules, cascade behaviour, error cases
- `test_cn.py` — CN creation (all 3 types), payment/stock/pricing effects, search, numbering

---

## Features (v2.2)

### New in v2.2 — PDF for All Documents + UX Fixes

- **PDF export extended to all document types:**
  - **GR Goods Receipts** — "Receive From" supplier box, line items table with unit cost and total cost row
  - **CR Cash Receipts** — voucher with customer name, INV reference, prominent amount box, signature line
  - **CP Cash Payments** — voucher with supplier name, GR reference, prominent amount box, signature line
  - **Bank Account Entries** — direction badge (green MONEY IN / red MONEY OUT), counterparty, INV/GR references, amount box
- **Business Details panel reorganised into 3 tabs** — Company, Tax & Legal, Documents — prevents content overflow
- **Save button always visible** — docked to the bottom of the Business Details panel
- **Tab content scrollable** — long forms scroll within the tab rather than clipping off-screen

---

## Features (v2.1)

### New in v2.1 — PDF Export

- **PDF button on DN Delivery Notes** — generates a branded A4 PDF saved to `~/Downloads/`
- **PDF button on INV Invoices** — generates a branded A4 PDF saved to `~/Downloads/`
- Both documents include:
  - Company logo (if set in Business Details), name, address, contact info
  - Document title, number and date in the configured theme colour (blue / green / monochrome)
  - Ship To / Bill To address box
  - Line items table with alternating row shading and themed header row
  - VAT number and Tax ID band (when configured)
  - Configurable footer text and page N / M numbering
- **INV invoice extras**: Payment Details box (due date, terms, bank account), colour-coded Outstanding amount (red if unpaid, green if settled), linked DN reference list
- **DN price toggle**: `doc_dn_show_prices = false` in Business Details hides Unit Price and Line Total columns
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
- **DN — Delivery Notes** — create draft, add/remove line items, issue DN (deducts stock)
- **INV — Invoices** — generate from DN or standalone; track payment status
- **GR — Goods Receipts** — record supplier deliveries, update stock on issue
- **SI/SO — Stock Movements** — internal stock adjustments (receipts and issues)

#### Finance
- **Cash Register** — CR income entries, CP expense entries with running balance
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
  Open Invoices, Open DN
- **11 report types** in the Reports dropdown with date-range filter and CSV export
