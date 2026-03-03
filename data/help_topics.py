"""data/help_topics.py — Help topic content for the Help panel."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HelpTopic:
    category: str
    title: str
    body: str
    keywords: list[str] = field(default_factory=list)


HELP_TOPICS: list[HelpTopic] = [
    # ── Getting Started ────────────────────────────────────────────────────────
    HelpTopic(
        category="Getting Started",
        title="Welcome",
        body=(
            "[b]Welcome to Northwind Traders[/b]\n\n"
            "Northwind Traders is a full-featured business management TUI "
            "application covering master data, documents, finance, analytics, "
            "and administration.\n\n"
            "• Use the sidebar on the left to navigate between panels\n"
            "• Press [b]?[/b] from any panel to return to this Help screen\n"
            "• Use the search box above to find specific topics"
        ),
        keywords=["intro", "overview", "about"],
    ),
    HelpTopic(
        category="Getting Started",
        title="Logging In",
        body=(
            "[b]Logging In[/b]\n\n"
            "When the application starts you are presented with a login screen.\n\n"
            "• Enter your [b]username[/b] and [b]PIN[/b]\n"
            "• Default admin account: [i]admin / 1234[/i]\n"
            "• After login the sidebar and panels become available\n"
            "• Your role determines which sections are visible"
        ),
        keywords=["login", "password", "pin", "auth", "sign in"],
    ),
    HelpTopic(
        category="Getting Started",
        title="Navigation",
        body=(
            "[b]Navigation[/b]\n\n"
            "The application uses a sidebar + content panel layout.\n\n"
            "• [b]Sidebar[/b] — click any item to switch panels\n"
            "• [b]Tab / Shift+Tab[/b] — move focus between widgets\n"
            "• [b]Arrow keys[/b] — navigate within tables and lists\n"
            "• [b]Enter[/b] — select / confirm\n"
            "• [b]Escape[/b] — close modals, cancel actions\n"
            "• [b]Ctrl+Q[/b] — quit (with confirmation)"
        ),
        keywords=["sidebar", "menu", "navigate", "move", "switch"],
    ),
    HelpTopic(
        category="Getting Started",
        title="User Roles",
        body=(
            "[b]User Roles[/b]\n\n"
            "The app supports role-based access control.\n\n"
            "• [b]user[/b] — view + create records in master data, documents, "
            "finance, and analytics\n"
            "• [b]manager[/b] — all of the above + delete records and documents\n"
            "• [b]admin[/b] — all of the above + cancel documents, issue CNs, "
            "manage users, access SQL Query, Business Details, and Settings\n\n"
            "Admin-only panels are hidden from the sidebar for non-admin users."
        ),
        keywords=["role", "permission", "access", "admin", "user", "manager", "delete", "cancel"],
    ),

    # ── Key Bindings ──────────────────────────────────────────────────────────
    HelpTopic(
        category="Key Bindings",
        title="Global Shortcuts",
        body=(
            "[b]Global Shortcuts[/b]\n\n"
            "These work from any panel (when no Input is focused):\n\n"
            "• [b]N[/b] — create a new record in the current panel\n"
            "• [b]F[/b] — focus the search / filter box\n"
            "• [b]?[/b] — open Help\n"
            "• [b]Ctrl+Q[/b] — quit with confirmation\n"
            "• [b]Ctrl+X[/b] — export current view to CSV\n"
            "• [b]Ctrl+I[/b] — import CSV into current panel\n"
            "• [b]R[/b] — refresh (Dashboard / Charts / Reports)\n"
            "• [b]Escape[/b] — close current modal"
        ),
        keywords=["shortcut", "hotkey", "key", "keyboard", "binding"],
    ),
    HelpTopic(
        category="Key Bindings",
        title="Panel Shortcuts",
        body=(
            "[b]Panel Shortcuts[/b]\n\n"
            "Per-panel bindings (active when no Input is focused):\n\n"
            "[b]Documents (DN / GR / INV):[/b]\n"
            "• [b]+[/b] — add a line item to the open document\n\n"
            "[b]Products:[/b]\n"
            "• [b]L[/b] — toggle Low Stock filter\n\n"
            "[b]Employees:[/b]\n"
            "• [b]O[/b] — open Org Chart view\n\n"
            "[b]SQL Query:[/b]\n"
            "• [b]Ctrl+R[/b] — run the current query\n\n"
            "[b]Reconciliation:[/b]\n"
            "• [b]U[/b] — All Unpaid view\n"
            "• [b]S[/b] — Statement view (per-customer/supplier ledger)\n"
            "• [b]P[/b] — Pay Invoice (AR only)\n"
            "• [b]A[/b] — Allocate a cash receipt or bank entry to an invoice\n\n"
            "Check the footer bar at the bottom for available actions "
            "in the current panel."
        ),
        keywords=["shortcut", "panel", "report", "delete", "edit",
                  "reconciliation", "allocate", "unpaid", "low stock", "org chart"],
    ),
    HelpTopic(
        category="Key Bindings",
        title="Modal Shortcuts",
        body=(
            "[b]Modal Shortcuts[/b]\n\n"
            "When a modal dialog is open:\n\n"
            "• [b]Escape[/b] — close / cancel the modal\n"
            "• [b]Enter[/b] — confirm / submit (when a button is focused)\n"
            "• [b]Tab / Shift+Tab[/b] — move between fields\n"
            "• [b]Arrow keys[/b] — navigate picker tables"
        ),
        keywords=["modal", "dialog", "popup", "escape"],
    ),

    # ── Master Data ───────────────────────────────────────────────────────────
    HelpTopic(
        category="Master Data",
        title="Dashboard",
        body=(
            "[b]Dashboard[/b]\n\n"
            "The Dashboard is your landing page after login.\n\n"
            "KPI cards shown:\n"
            "• Orders Today, Revenue MTD, Low Stock count\n"
            "• Pending Orders, Avg Fulfilment Days, MoM trend (↑/↓)\n"
            "• Cash Register Balance, Bank Account Balance\n"
            "• Open Invoices, Open DNs\n\n"
            "• Press [b]R[/b] to refresh KPI data\n"
            "• Displays recent orders in a summary table"
        ),
        keywords=["home", "kpi", "summary", "landing"],
    ),
    HelpTopic(
        category="Master Data",
        title="Customers",
        body=(
            "[b]Customers[/b]\n\n"
            "Manage your customer database.\n\n"
            "• [b]N[/b] — add a new customer\n"
            "• [b]F[/b] — search by company name, contact, or city\n"
            "• Click a row to edit customer details\n"
            "• Customers are linked to orders, invoices, and credit notes\n"
            "• CSV import and export supported"
        ),
        keywords=["customer", "client", "company", "contact"],
    ),
    HelpTopic(
        category="Master Data",
        title="Orders",
        body=(
            "[b]Orders[/b]\n\n"
            "Create and manage sales orders.\n\n"
            "• [b]N[/b] — new order with customer and employee pickers\n"
            "• Add order lines with product, quantity, unit price, discount\n"
            "• Orders flow into delivery notes and invoices\n"
            "• Filter by customer, date range, or status"
        ),
        keywords=["order", "sale", "purchase", "line item"],
    ),
    HelpTopic(
        category="Master Data",
        title="Products",
        body=(
            "[b]Products[/b]\n\n"
            "Maintain the product catalog.\n\n"
            "• [b]N[/b] — add a new product\n"
            "• Fields: name, supplier, category, unit price, stock levels\n"
            "• Stock is adjusted by DN (out), GR (in), and SI/SO movements\n"
            "• Low-stock alerts appear in the Reports panel\n"
            "• CSV import and export supported"
        ),
        keywords=["product", "item", "stock", "inventory", "catalog"],
    ),
    HelpTopic(
        category="Master Data",
        title="Employees",
        body=(
            "[b]Employees[/b]\n\n"
            "Manage employee records.\n\n"
            "• [b]N[/b] — add a new employee\n"
            "• Fields: name, title, reports-to, hire date, region\n"
            "• Employees are linked to orders as the salesperson\n"
            "• Org chart available via the Employees panel"
        ),
        keywords=["employee", "staff", "salesperson", "hr"],
    ),
    HelpTopic(
        category="Master Data",
        title="Suppliers",
        body=(
            "[b]Suppliers[/b]\n\n"
            "Manage supplier information.\n\n"
            "• [b]N[/b] — add a new supplier\n"
            "• Fields: company name, contact, address, phone\n"
            "• Suppliers are linked to products\n"
            "• CSV import and export supported"
        ),
        keywords=["supplier", "vendor", "provider"],
    ),
    HelpTopic(
        category="Master Data",
        title="Categories",
        body=(
            "[b]Categories[/b]\n\n"
            "Organize products into categories.\n\n"
            "• [b]N[/b] — add a new category\n"
            "• Fields: category name, description\n"
            "• Each product belongs to one category\n"
            "• CSV import and export supported"
        ),
        keywords=["category", "group", "classify"],
    ),
    HelpTopic(
        category="Master Data",
        title="Shippers",
        body=(
            "[b]Shippers[/b]\n\n"
            "Manage shipping carriers.\n\n"
            "• [b]N[/b] — add a new shipper\n"
            "• Fields: company name, phone\n"
            "• Shippers are referenced in orders for delivery"
        ),
        keywords=["shipper", "carrier", "delivery", "freight"],
    ),
    HelpTopic(
        category="Master Data",
        title="Regions",
        body=(
            "[b]Regions & Territories[/b]\n\n"
            "Define geographic regions and territories.\n\n"
            "• Two tabs: Regions and Territories\n"
            "• Territories belong to a region\n"
            "• Employees can be assigned to territories"
        ),
        keywords=["region", "territory", "geography", "area"],
    ),

    # ── Documents ─────────────────────────────────────────────────────────────
    HelpTopic(
        category="Documents",
        title="DN — Delivery Notes",
        body=(
            "[b]DN — Delivery Notes[/b]\n\n"
            "Track the dispatch of goods to customers.\n\n"
            "[b]Workflow[/b]\n"
            "• Create a draft DN linked to an order\n"
            "• Add line items (products + quantities)\n"
            "• [b]Issue[/b] — confirms dispatch and reduces stock\n"
            "• [b]Cancel[/b] — reverses stock changes (admin only)\n\n"
            "[b]Status flow:[/b]  Draft → Issued → (Cancelled)"
        ),
        keywords=["delivery", "dispatch", "shipment", "dn"],
    ),
    HelpTopic(
        category="Documents",
        title="INV — Invoices",
        body=(
            "[b]INV — Invoices[/b]\n\n"
            "Generate invoices for delivered goods.\n\n"
            "[b]Workflow[/b]\n"
            "• Create from an issued DN or manually\n"
            "• Add line items with pricing\n"
            "• [b]Issue[/b] — finalizes the invoice\n"
            "• [b]Cancel[/b] — voids the invoice (admin only)\n\n"
            "Issued invoices can generate Credit Notes if needed."
        ),
        keywords=["invoice", "bill", "billing", "inv"],
    ),
    HelpTopic(
        category="Documents",
        title="CN — Credit Notes",
        body=(
            "[b]CN — Credit Notes[/b]\n\n"
            "Issue credit notes against invoices.\n\n"
            "[b]Workflow[/b]\n"
            "• Create linked to an issued invoice\n"
            "• Specify reason and line items for credit\n"
            "• [b]Issue[/b] — finalizes and may reverse stock\n"
            "• Used for returns, corrections, and adjustments"
        ),
        keywords=["credit", "refund", "return", "cn"],
    ),
    HelpTopic(
        category="Documents",
        title="GR — Goods Receipt",
        body=(
            "[b]GR — Goods Receipt[/b]\n\n"
            "Record incoming goods from suppliers.\n\n"
            "[b]Workflow[/b]\n"
            "• Create a GR with supplier and product details\n"
            "• Add line items (products + quantities)\n"
            "• [b]Issue[/b] — confirms receipt and increases stock\n"
            "• [b]Cancel[/b] — reverses stock changes (admin only)\n\n"
            "[b]Status flow:[/b]  Draft → Issued → (Cancelled)"
        ),
        keywords=["goods receipt", "receiving", "inbound", "gr"],
    ),
    HelpTopic(
        category="Documents",
        title="SI/SO — Stock Movements",
        body=(
            "[b]SI/SO — Stock Issue / Stock Out[/b]\n\n"
            "Manual stock adjustments outside the normal document flow.\n\n"
            "• [b]SI (Stock Issue)[/b] — add stock (e.g. corrections, "
            "transfers in)\n"
            "• [b]SO (Stock Out)[/b] — remove stock (e.g. damage, "
            "write-offs)\n\n"
            "Each movement records product, quantity, date, and reason."
        ),
        keywords=["stock", "inventory", "adjustment", "si", "so", "movement"],
    ),

    # ── Finance ───────────────────────────────────────────────────────────────
    HelpTopic(
        category="Finance",
        title="Cash Register",
        body=(
            "[b]Cash Register[/b]\n\n"
            "Track cash receipts and payments.\n\n"
            "• Two tabs: [b]Receipts[/b] (money in) and [b]Payments[/b] "
            "(money out)\n"
            "• Each entry: date, description, amount, reference\n"
            "• Running balance displayed at the top\n"
            "• [b]CR (Cash Receipt)[/b] entries link to INV references\n"
            "• [b]CP (Cash Payment)[/b] entries link to GR references\n"
            "• Entries can be allocated to open invoices via the "
            "Reconciliation panel"
        ),
        keywords=["cash", "receipt", "payment", "petty cash", "register",
                  "cr", "cp", "cash receipt", "cash payment"],
    ),
    HelpTopic(
        category="Finance",
        title="Bank Account",
        body=(
            "[b]Bank Account[/b]\n\n"
            "Track bank transactions.\n\n"
            "• Record money in and money out entries\n"
            "• Each entry: date, description, amount, reference\n"
            "• Running balance displayed at the top\n"
            "• Link entries to invoices, credit notes, or cash transfers\n"
            "• Bank entries can be allocated to open INV or GR documents "
            "via the Reconciliation panel\n"
            "• Use bank transfers to record movements between "
            "the bank and cash register"
        ),
        keywords=["bank", "deposit", "withdrawal", "transfer", "account",
                  "bank transfer", "money in", "money out"],
    ),

    HelpTopic(
        category="Finance",
        title="Reconciliation (AR/AP)",
        body=(
            "[b]Reconciliation — Accounts Receivable & Payable[/b]\n\n"
            "[b]AR (Accounts Receivable)[/b] — track what customers owe you\n"
            "• Default view: All Unpaid invoices across all customers\n"
            "• [b]U[/b] → All Unpaid view\n"
            "• [b]S[/b] → Statement (per-customer ledger)\n"
            "• [b]P[/b] → Pay Invoice (register a manual payment)\n"
            "• [b]A[/b] → Allocate a cash receipt or bank entry to an invoice\n"
            "• Filter by customer with the ▼ Filter button\n\n"
            "[b]AP (Accounts Payable)[/b] — track what you owe suppliers\n"
            "• Default view: All Unpaid goods receipts across all suppliers\n"
            "• [b]U[/b] / [b]S[/b] / [b]A[/b] work the same as AR\n"
            "• P is not available on AP (no direct supplier pay)\n\n"
            "Use the AR Aging / AP Aging reports for an overdue overview."
        ),
        keywords=["reconciliation", "ar", "ap", "accounts receivable",
                  "accounts payable", "unpaid", "aging", "payment",
                  "allocate", "statement", "outstanding"],
    ),

    # ── Analytics ─────────────────────────────────────────────────────────────
    HelpTopic(
        category="Analytics",
        title="Reports",
        body=(
            "[b]Reports[/b]\n\n"
            "Run pre-built business reports.\n\n"
            "• Select a report type from the dropdown\n"
            "• Press [b]R[/b] to run the selected report\n"
            "• Export results to CSV with [b]Ctrl+X[/b]\n\n"
            "[b]Available report types:[/b]\n"
            "  – Sales by Customer / Product / Employee\n"
            "  – Top 10 Products by Revenue\n"
            "  – Low Stock Alert\n"
            "  – Orders by Date Range\n"
            "  – Monthly Revenue Trend\n"
            "  – Order Fulfilment Time\n"
            "  – Category Revenue\n"
            "  – Repeat Customers\n"
            "  – Overdue Orders\n"
            "  – Cash & Bank Status\n"
            "  – AR Aging / AP Aging (Payables)\n"
            "  – Incoming Payments (30 days)\n"
            "  – Supplier Spending\n"
            "  – Stock Valuation"
        ),
        keywords=["report", "analysis", "analytics", "sales",
                  "aging", "forecast", "supplier spending",
                  "stock valuation", "fulfilment"],
    ),
    HelpTopic(
        category="Analytics",
        title="Charts",
        body=(
            "[b]Charts[/b]\n\n"
            "Visual analytics using text-based charts.\n\n"
            "• Multiple chart types available via tabs\n"
            "• KPI summary bar at the top\n"
            "• Filter by date range\n"
            "• Charts render as ASCII art within the terminal"
        ),
        keywords=["chart", "graph", "visual", "ascii", "plot"],
    ),

    # ── Import/Export ─────────────────────────────────────────────────────────
    HelpTopic(
        category="Import/Export",
        title="CSV Export",
        body=(
            "[b]CSV Export[/b]\n\n"
            "Export data from any master data panel to CSV.\n\n"
            "• Press [b]Ctrl+X[/b] in a panel to export\n"
            "• A file browser lets you choose the save location\n"
            "• Exported files use the panel name as the default filename\n"
            "• Reports can also be exported to CSV"
        ),
        keywords=["export", "csv", "download", "save", "file"],
    ),
    HelpTopic(
        category="Import/Export",
        title="CSV Import",
        body=(
            "[b]CSV Import[/b]\n\n"
            "Import data from CSV files into master data panels.\n\n"
            "• Supported panels: Customers, Suppliers, Products, Categories\n"
            "• CSV headers must match the expected column names\n"
            "• Alias mappings allow using display headers from exports\n"
            "• Validation errors are reported per row"
        ),
        keywords=["import", "csv", "upload", "load", "file"],
    ),
    HelpTopic(
        category="Import/Export",
        title="PDF Export",
        body=(
            "[b]PDF Export[/b]\n\n"
            "All 7 document types support PDF export: "
            "[b]DN, INV, CN, GR, CR, CP, Bank Entry[/b]\n\n"
            "• Click [b][PDF][/b] in any document detail modal\n"
            "• A file browser opens to choose the save location\n"
            "• PDF includes:\n"
            "  – Company header (logo, name, address)\n"
            "  – Branded colour theme\n"
            "  – Line items table with totals\n"
            "  – QR code (scannable, encodes key document fields)\n\n"
            "[b]Configure branding in Business Details (Admin only):[/b]\n"
            "• Company logo — Browse button copies image to assets/\n"
            "• Colour theme, document titles, footer text\n"
            "• QR on/off toggle\n"
            "• VAT number and Tax ID printed on applicable documents"
        ),
        keywords=["pdf", "print", "document", "export",
                  "qr", "qr code", "logo", "branding", "theme", "footer"],
    ),

    # ── Admin ─────────────────────────────────────────────────────────────────
    HelpTopic(
        category="Admin",
        title="SQL Query",
        body=(
            "[b]SQL Query[/b]\n\n"
            "Run raw SQL queries against the database.\n\n"
            "• [b]Admin only[/b] — not visible to regular users\n"
            "• Type SQL in the text area and press the Run button\n"
            "• Results displayed in a DataTable below\n"
            "• Supports SELECT, INSERT, UPDATE, DELETE\n"
            "• Use with caution — changes are immediate"
        ),
        keywords=["sql", "query", "database", "admin"],
    ),
    HelpTopic(
        category="Admin",
        title="Users & Roles",
        body=(
            "[b]Users & Roles[/b]\n\n"
            "Manage application user accounts.\n\n"
            "• [b]Admin only[/b]\n"
            "• Create, edit, and delete user accounts\n"
            "• Assign roles (user / manager / admin)\n"
            "• Set or reset user PINs\n\n"
            "See [b]Getting Started → User Roles[/b] for a full "
            "description of each role's permissions."
        ),
        keywords=["user", "role", "account", "admin", "permission", "manager"],
    ),
    HelpTopic(
        category="Admin",
        title="Business Details",
        body=(
            "[b]Business Details[/b]\n\n"
            "Configure company information and PDF branding. "
            "[b]Admin only.[/b]\n\n"
            "Three tabs:\n\n"
            "[b]Company tab[/b]\n"
            "• Company name, address, city, postal, country, phone, "
            "email, website\n"
            "• [b]Company Logo[/b] — Browse button; file copied to "
            "assets/logo.<ext>\n"
            "  Recommended: PNG, transparent background, 300×100 px, max 1 MB\n\n"
            "[b]Tax & Legal tab[/b]\n"
            "• VAT Number, Tax ID / NIP, Bank Account\n\n"
            "[b]Documents tab[/b]\n"
            "• Footer note, colour theme (Default / Blue / Green / Monochrome)\n"
            "• Custom titles for DN / INV / GR documents\n"
            "• Toggle: Show unit prices on DN delivery notes\n"
            "• Toggle: Show QR codes on all documents"
        ),
        keywords=["business", "company", "config", "branding",
                  "logo", "vat", "tax", "theme", "footer",
                  "qr", "colour", "pdf settings"],
    ),
    HelpTopic(
        category="Admin",
        title="Settings",
        body=(
            "[b]Settings[/b]\n\n"
            "Application-wide settings.\n\n"
            "• [b]Admin only[/b]\n"
            "• Theme selection (persisted per session)\n"
            "• Demo data management — load or reset sample data\n"
            "• Other application preferences"
        ),
        keywords=["settings", "preferences", "theme", "config", "demo"],
    ),

    # ── Troubleshooting ───────────────────────────────────────────────────────
    HelpTopic(
        category="Troubleshooting",
        title="Common Issues",
        body=(
            "[b]Common Issues[/b]\n\n"
            "• [b]Can't see Admin panels?[/b]\n"
            "  You need admin role. Ask an administrator to upgrade "
            "your account.\n\n"
            "• [b]Data not refreshing?[/b]\n"
            "  Click the panel name in the sidebar to force a refresh.\n\n"
            "• [b]Modal won't close?[/b]\n"
            "  Press [b]Escape[/b] to dismiss any open modal."
        ),
        keywords=["problem", "issue", "bug", "error", "fix"],
    ),
    HelpTopic(
        category="Troubleshooting",
        title="Stock Issues",
        body=(
            "[b]Stock Issues[/b]\n\n"
            "• [b]Stock went negative?[/b]\n"
            "  Check DN and SO entries — cancel incorrect ones.\n"
            "  Use GR or SI to correct stock levels.\n\n"
            "• [b]Stock doesn't match?[/b]\n"
            "  Run the Low Stock Alert report to audit.\n"
            "  Check SI/SO panel for manual adjustments."
        ),
        keywords=["stock", "inventory", "negative", "mismatch"],
    ),
    HelpTopic(
        category="Troubleshooting",
        title="Keyboard Not Working",
        body=(
            "[b]Keyboard Shortcuts Not Working[/b]\n\n"
            "• Shortcuts like [b]N[/b], [b]F[/b], [b]?[/b] only work "
            "when no Input or TextArea widget has focus\n"
            "• Press [b]Escape[/b] or [b]Tab[/b] to move focus away "
            "from text fields\n"
            "• Check the footer bar — it shows available bindings "
            "for the current context"
        ),
        keywords=["keyboard", "shortcut", "not working", "focus", "input"],
    ),

    # ── FAQ ───────────────────────────────────────────────────────────────────
    HelpTopic(
        category="FAQ",
        title="How do I create an invoice?",
        body=(
            "[b]How do I create an invoice?[/b]\n\n"
            "Standard workflow:\n\n"
            "1. Create a [b]DN (Delivery Note)[/b] linked to an order "
            "(Documents → DN → N)\n"
            "2. Add line items, then click [b]Issue[/b] — stock is reduced\n"
            "3. Open [b]Documents → INV[/b] and press [b]N[/b] — link to the "
            "issued DN\n"
            "4. Add pricing line items, then click [b]Issue[/b] — invoice is "
            "finalised\n"
            "5. The invoice now appears in AR Reconciliation as unpaid"
        ),
        keywords=["invoice", "create", "workflow", "billing"],
    ),
    HelpTopic(
        category="FAQ",
        title="How do I pay an invoice?",
        body=(
            "[b]How do I pay an invoice?[/b]\n\n"
            "1. Go to [b]Finance → Reconciliation[/b] (AR tab)\n"
            "2. Press [b]U[/b] to see All Unpaid invoices\n"
            "3. Select the invoice and press [b]P[/b] — Pay Invoice\n"
            "4. Enter the payment amount and date, confirm\n"
            "5. Alternatively, press [b]A[/b] — Allocate — to match an "
            "existing Cash Receipt or Bank entry to the invoice"
        ),
        keywords=["pay", "payment", "invoice", "reconciliation"],
    ),
    HelpTopic(
        category="FAQ",
        title="How do I cancel a document?",
        body=(
            "[b]How do I cancel a document?[/b]\n\n"
            "Cancellation requires [b]admin[/b] role.\n\n"
            "1. Open the document (DN / INV / GR / etc.)\n"
            "2. Click the [b]Cancel[/b] button in the detail modal\n"
            "3. Confirm the cancellation dialog\n"
            "4. Stock and financial effects are automatically reversed\n\n"
            "Note: a CN (Credit Note) is the preferred way to reverse "
            "a financed invoice — use Cancel only for administrative corrections."
        ),
        keywords=["cancel", "undo", "void", "reverse"],
    ),
    HelpTopic(
        category="FAQ",
        title="Why can't I delete this record?",
        body=(
            "[b]Why can't I delete this record?[/b]\n\n"
            "Deletion is blocked when the record is referenced by other data:\n\n"
            "• A [b]Customer[/b] with orders cannot be deleted\n"
            "• A [b]Product[/b] on any order or document cannot be deleted\n"
            "• A [b]Supplier[/b] linked to products cannot be deleted\n\n"
            "You need [b]manager[/b] or [b]admin[/b] role to delete records.\n\n"
            "To remove a record: first reassign or remove its dependent data, "
            "then delete."
        ),
        keywords=["delete", "guard", "blocked", "error", "referential"],
    ),
    HelpTopic(
        category="FAQ",
        title="How do I correct a wrong invoice?",
        body=(
            "[b]How do I correct a wrong invoice?[/b]\n\n"
            "Use a [b]Credit Note (CN)[/b] to reverse or adjust an issued "
            "invoice:\n\n"
            "1. Go to [b]Documents → CN[/b] and press [b]N[/b]\n"
            "2. Link the CN to the original issued invoice\n"
            "3. Add line items for the amount to credit\n"
            "4. Click [b]Issue[/b] — the credit is applied\n\n"
            "For a full reversal, match all line items from the original invoice. "
            "For a partial correction, enter only the difference."
        ),
        keywords=["credit note", "correction", "refund", "cn"],
    ),
    HelpTopic(
        category="FAQ",
        title="How do I add a company logo to PDFs?",
        body=(
            "[b]How do I add a company logo to PDFs?[/b]\n\n"
            "1. Go to [b]Admin → Business Details[/b] (admin only)\n"
            "2. On the [b]Company[/b] tab, click [b]Browse[/b] next to "
            "Company Logo\n"
            "3. Select an image file (PNG recommended, 300×100 px, max 1 MB)\n"
            "4. The file is copied to [i]assets/logo.<ext>[/i] automatically\n"
            "5. Click [b]Save[/b] — the logo now appears on all generated PDFs\n\n"
            "For best results: transparent background, landscape orientation."
        ),
        keywords=["logo", "pdf", "branding", "image"],
    ),
    HelpTopic(
        category="FAQ",
        title="What's the difference between Cash Register and Bank Account?",
        body=(
            "[b]Cash Register vs Bank Account[/b]\n\n"
            "[b]Cash Register[/b]\n"
            "• Physical cash on hand\n"
            "• CR entries (Cash Receipts) link to customer invoices\n"
            "• CP entries (Cash Payments) link to supplier goods receipts\n\n"
            "[b]Bank Account[/b]\n"
            "• Electronic bank balance\n"
            "• Records deposits, withdrawals, and transfers\n"
            "• Bank entries can be allocated to open invoices via Reconciliation\n\n"
            "Both panels show a running balance and support CSV export. "
            "Use [b]Finance → Reconciliation[/b] to match entries to documents."
        ),
        keywords=["cash", "bank", "difference"],
    ),
    HelpTopic(
        category="FAQ",
        title="How do I see all unpaid invoices?",
        body=(
            "[b]How do I see all unpaid invoices?[/b]\n\n"
            "1. Go to [b]Finance → Reconciliation[/b]\n"
            "2. Make sure the [b]AR[/b] (Accounts Receivable) tab is active\n"
            "3. Press [b]U[/b] — switches to All Unpaid view\n"
            "   All outstanding invoices across all customers are listed\n\n"
            "To see unpaid invoices for a single customer:\n"
            "4. Use the ▼ Filter button to select a customer\n"
            "5. Press [b]S[/b] — Statement view shows their ledger\n\n"
            "Run the [b]AR Aging[/b] report (Analytics → Reports) for an "
            "overdue breakdown by aging bucket."
        ),
        keywords=["unpaid", "outstanding", "ar", "receivable"],
    ),
    HelpTopic(
        category="FAQ",
        title="How do I import existing data?",
        body=(
            "[b]How do I import existing data?[/b]\n\n"
            "CSV import is supported for: Customers, Suppliers, Products, "
            "Categories.\n\n"
            "1. Prepare a CSV file with headers matching the expected columns\n"
            "   (Headers from a CSV export of the same panel will always work)\n"
            "2. Navigate to the panel (e.g. Master Data → Customers)\n"
            "3. Press [b]Ctrl+I[/b] — a file browser opens\n"
            "4. Select your CSV file and confirm\n"
            "5. Validation errors are reported per row — fix and re-import\n\n"
            "Tip: export a small sample first to see the expected column format."
        ),
        keywords=["import", "csv", "migrate", "upload"],
    ),
    HelpTopic(
        category="FAQ",
        title="How do I set up company branding for PDFs?",
        body=(
            "[b]How do I set up company branding for PDFs?[/b]\n\n"
            "Go to [b]Admin → Business Details[/b] (admin role required).\n\n"
            "[b]Step 1 — Company info[/b]\n"
            "• Fill in company name, address, phone, email on the Company tab\n"
            "• Upload your logo via the Browse button\n\n"
            "[b]Step 2 — Tax & Legal[/b]\n"
            "• Enter VAT Number and Tax ID — these print on applicable documents\n\n"
            "[b]Step 3 — Documents tab[/b]\n"
            "• Choose a colour theme (Default / Blue / Green / Monochrome)\n"
            "• Set a footer note (e.g. payment terms, thank-you message)\n"
            "• Optionally enable QR codes and customise document titles\n\n"
            "Click [b]Save[/b] — all future PDFs will use the new settings."
        ),
        keywords=["branding", "pdf", "theme", "setup"],
    ),
]
