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
            "• [b]Admin[/b] — full access to all panels including SQL, "
            "Users, Business Details, and Settings\n"
            "• [b]User[/b] — access to master data, documents, finance, "
            "and analytics panels\n\n"
            "Admin-only panels are hidden from the sidebar for non-admin users."
        ),
        keywords=["role", "permission", "access", "admin", "user"],
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
            "• [b]Escape[/b] — close current modal"
        ),
        keywords=["shortcut", "hotkey", "key", "keyboard", "binding"],
    ),
    HelpTopic(
        category="Key Bindings",
        title="Panel Shortcuts",
        body=(
            "[b]Panel Shortcuts[/b]\n\n"
            "Many panels define their own key bindings:\n\n"
            "• [b]R[/b] — run report (Reports panel)\n"
            "• [b]Ctrl+X[/b] — export to CSV\n"
            "• [b]D[/b] — delete selected record\n"
            "• [b]E[/b] — edit selected record\n\n"
            "Check the footer bar at the bottom for available actions "
            "in the current panel."
        ),
        keywords=["shortcut", "panel", "report", "delete", "edit"],
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
            "• Shows KPI cards: total customers, orders, products, revenue\n"
            "• Displays recent orders in a summary table\n"
            "• Data refreshes each time you navigate to the Dashboard"
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
            "• Link entries to invoices or credit notes"
        ),
        keywords=["cash", "receipt", "payment", "petty cash", "register"],
    ),
    HelpTopic(
        category="Finance",
        title="Bank Account",
        body=(
            "[b]Bank Account[/b]\n\n"
            "Track bank transactions.\n\n"
            "• Record deposits, withdrawals, and transfers\n"
            "• Each entry: date, description, amount, reference\n"
            "• Running balance displayed at the top\n"
            "• Link entries to invoices, credit notes, or cash transfers"
        ),
        keywords=["bank", "deposit", "withdrawal", "transfer", "account"],
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
            "• Available reports include:\n"
            "  – Sales by Customer / Product / Employee\n"
            "  – Top 10 Products by Revenue\n"
            "  – Low Stock Alert\n"
            "  – Monthly Revenue Trend\n"
            "  – AR Aging and more\n"
            "• Export results to CSV with [b]Ctrl+X[/b]"
        ),
        keywords=["report", "analysis", "analytics", "sales"],
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
            "Generate PDF documents from issued documents.\n\n"
            "• Available for Invoices and other issued documents\n"
            "• Configure company details in Business Details panel\n"
            "• PDF includes header, line items, and totals\n"
            "• Saved to the exports directory"
        ),
        keywords=["pdf", "print", "document", "export"],
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
            "• Assign roles (admin or user)\n"
            "• Set or reset user PINs"
        ),
        keywords=["user", "role", "account", "admin", "permission"],
    ),
    HelpTopic(
        category="Admin",
        title="Business Details",
        body=(
            "[b]Business Details[/b]\n\n"
            "Configure your company information.\n\n"
            "• [b]Admin only[/b]\n"
            "• Company name, address, tax ID, contact info\n"
            "• Bank details for invoices and documents\n"
            "• This information appears on generated PDFs"
        ),
        keywords=["business", "company", "config", "branding"],
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
]
