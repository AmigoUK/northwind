"""data/demo.py — Demo data management: insert and clean full DB lifecycle."""
from __future__ import annotations

import random
import time
from datetime import date, timedelta

from db import get_connection

# Transactional tables checked / cleaned (in FK-safe DELETE order)
_TRANSACTIONAL_TABLES = [
    "CN_Items", "CN",
    "INV_DN", "DN_Items", "GR_Items", "SI_Items", "SO_Items",
    "CR", "CP", "BankEntry",
    "INV", "DN", "GR", "SI", "SO",
    "DocSequence",
]

# Master tables deleted after transactional ones (FK-safe order)
_MASTER_TABLES = [
    "OrderDetails",   # FK → Orders, Products
    "Orders",          # FK → Customers, Employees, Shippers
    "Products",        # FK → Suppliers, Categories
    "Territories",     # FK → Region
    "Employees",       # self-FK ReportsTo (nullified before delete)
    "Customers",
    "Shippers",
    "Suppliers",
    "Region",          # note: table name is "Region" not "Regions"
    "Categories",
]

# Seasonality multipliers by (year, month)
_SEASONALITY = {
    (2025, 1): 0.8, (2025, 2): 0.9, (2025, 3): 1.0, (2025, 4): 1.0,
    (2025, 5): 1.1, (2025, 6): 1.1, (2025, 7): 0.9, (2025, 8): 0.8,
    (2025, 9): 1.1, (2025, 10): 1.2, (2025, 11): 1.3, (2025, 12): 1.2,
    (2026, 1): 0.7, (2026, 2): 0.8,
}

# Realistic stock-intake reasons for SI documents
_SI_REASONS = [
    "Inventory count — surplus found",
    "Supplier delivery correction — extra units",
    "Customer return — goods restocked",
    "Inter-location transfer inbound",
]

# Additional customers to reach 30 total
_EXTRA_CUSTOMERS = [
    ("CACTU", "Cactus Comidas para llevar", "Patricio Simpson", "Sales Agent", "Cerrito 333", "Buenos Aires", None, "1010", "Argentina", "(1) 135-5555", "(1) 135-4892"),
    ("CENTC", "Centro comercial Moctezuma", "Francisco Chang", "Marketing Manager", "Sierras de Granada 9993", "México D.F.", None, "05022", "Mexico", "(5) 555-3392", "(5) 555-7293"),
    ("CHOPS", "Chop-suey Chinese", "Yang Wang", "Owner", "Hauptstr. 29", "Bern", None, "3012", "Switzerland", "0452-076545", None),
    ("COMMI", "Comércio Mineiro", "Pedro Afonso", "Sales Associate", "Av. dos Lusíadas, 23", "São Paulo", "SP", "05432-043", "Brazil", "(11) 555-7647", None),
    ("CONSH", "Consolidated Holdings", "Elizabeth Brown", "Sales Representative", "Berkeley Gardens 12 Brewery", "London", None, "WX1 6LT", "UK", "(171) 555-2282", "(171) 555-9199"),
    ("DRACD", "Drachenblut Delikatessen", "Sven Ottlieb", "Order Administrator", "Walserweg 21", "Aachen", None, "52066", "Germany", "0241-039123", "0241-059428"),
    ("DUMON", "Du monde entier", "Janine Labrune", "Owner", "67, rue des Cinquante Otages", "Nantes", None, "44000", "France", "40.67.88.88", "40.67.89.89"),
    ("EASTC", "Eastern Connection", "Ann Devon", "Sales Agent", "35 King George", "London", None, "WX3 6FW", "UK", "(171) 555-0297", "(171) 555-3373"),
    ("ERNSH", "Ernst Handel", "Roland Mendel", "Sales Manager", "Kirchgasse 6", "Graz", None, "8010", "Austria", "7675-3425", "7675-3426"),
    ("FAMIA", "Familia Arquibaldo", "Aria Cruz", "Marketing Assistant", "Rua Orós, 92", "São Paulo", "SP", "05442-030", "Brazil", "(11) 555-9857", None),
    ("FRANK", "Frankenversand", "Peter Franken", "Marketing Manager", "Berliner Platz 43", "München", None, "80805", "Germany", "089-0877310", "089-0877451"),
    ("GALED", "Galería del gastrónomo", "Eduardo Saavedra", "Marketing Manager", "Rambla de Cataluña, 23", "Barcelona", None, "08022", "Spain", "(93) 203 4560", "(93) 203 4561"),
    ("GODOS", "Godos Cocina Típica", "José Pedro Freyre", "Sales Manager", "C/ Romero, 33", "Sevilla", None, "41101", "Spain", "(95) 555 82 82", None),
    ("GOURL", "Gourmet Lanchonetes", "André Fonseca", "Sales Associate", "Av. Brasil, 442", "Campinas", "SP", "04876-786", "Brazil", "(11) 555-9482", None),
    ("GREAL", "Great Lakes Food Market", "Howard Snyder", "Marketing Manager", "2732 Baker Blvd.", "Eugene", "OR", "97403", "USA", "(503) 555-7555", None),
    ("HANAR", "Hanari Carnes", "Mario Pontes", "Accounting Manager", "Rua do Paço, 67", "Rio de Janeiro", "RJ", "05454-876", "Brazil", "(21) 555-0091", "(21) 555-8765"),
    ("HILAA", "HILARION-Abastos", "Carlos Hernández", "Sales Representative", "Carrera 22 con Ave. Carlos Soublette #8-35", "San Cristóbal", "Táchira", "5022", "Venezuela", "(5) 555-1340", "(5) 555-1948"),
    ("HUNGC", "Hungry Coyote Import Store", "Yoshi Latimer", "Sales Representative", "City Center Plaza 516 Main St.", "Elgin", "OR", "97827", "USA", "(503) 555-6874", "(503) 555-2376"),
    ("ISLAT", "Island Trading", "Helen Bennett", "Marketing Manager", "Garden House Crowther Way", "Cowes", "Isle of Wight", "PO31 7PJ", "UK", "(198) 555-8888", None),
    ("KOENE", "Königlich Essen", "Philip Cramer", "Sales Associate", "Maubelstr. 90", "Brandenburg", None, "14776", "Germany", "0555-09876", None),
]

# Additional suppliers to reach 15 total
_EXTRA_SUPPLIERS = [
    (11, "Heli Süßwaren GmbH & Co. KG", "Petra Winkler", "Sales Manager", "Tiergartenstraße 5", "Berlin", None, "10785", "Germany", "(010) 9984510", None, None),
    (12, "Plutzer Lebensmittelgroßmärkte AG", "Martin Bein", "International Marketing Mgr.", "Bogenallee 51", "Frankfurt", None, "60439", "Germany", "(069) 992755", None, "Plutzer (on the World Wide Web)#http://www.plutzer.de#"),
    (13, "Nord-Ost-Fisch Handelsgesellschaft mbH", "Sven Petersen", "Coordinator Foreign Markets", "Frahmredder 112a", "Cuxhaven", None, "27478", "Germany", "(04721) 8713", "(04721) 8714", None),
    (14, "Formaggi Fortini s.r.l.", "Elio Rossi", "Sales Representative", "Viale Dante, 75", "Ravenna", None, "48100", "Italy", "(0544) 60323", "(0544) 60603", "#FORMAGGI.htm#"),
    (15, "Norske Meierier", "Beate Vileid", "Marketing Manager", "Hatlevegen 5", "Sandvika", None, "1320", "Norway", "(0)2-953010", None, None),
]

# Additional products to reach 50 total (pid 21-50)
_EXTRA_PRODUCTS = [
    (21, "Sir Rodney's Scones", 8, 3, "24 pkgs. x 4 pieces", 10.00, 0, 0, 5, 0),
    (22, "Gustaf's Knäckebröd", 9, 5, "24 - 500 g pkgs.", 21.00, 0, 0, 25, 0),
    (23, "Tunnbröd", 9, 5, "12 - 250 g pkgs.", 9.00, 0, 0, 25, 0),
    (24, "Guaraná Fantástica", 10, 1, "12 - 355 ml cans", 4.50, 0, 0, 0, 0),
    (25, "NuNuCa Nuß-Nougat-Creme", 11, 3, "20 - 450 g glasses", 14.00, 0, 0, 30, 0),
    (26, "Gumbär Gummibärchen", 11, 3, "100 - 250 g bags", 31.23, 0, 0, 0, 0),
    (27, "Schoggi Schokolade", 11, 3, "100 - 100 g pieces", 43.90, 0, 0, 0, 0),
    (28, "Rössle Sauerkraut", 12, 7, "25 - 825 g cans", 45.60, 0, 0, 0, 0),
    (29, "Thüringer Rostbratwurst", 12, 6, "50 bags x 30 sausgs.", 123.79, 0, 0, 0, 0),
    (30, "Nord-Ost Matjeshering", 13, 8, "10 - 200 g glasses", 25.89, 0, 0, 15, 0),
    (31, "Gorgonzola Telino", 14, 4, "12 - 100 g pkgs", 12.50, 0, 0, 20, 0),
    (32, "Mascarpone Fabioli", 14, 4, "24 - 200 g pkgs.", 32.00, 0, 0, 0, 0),
    (33, "Geitost", 15, 4, "500 g", 2.50, 0, 0, 20, 0),
    (34, "Sasquatch Ale", 1, 1, "24 - 12 oz bottles", 14.00, 0, 0, 15, 0),
    (35, "Steeleye Stout", 1, 1, "24 - 12 oz bottles", 18.00, 0, 0, 15, 0),
    (36, "Inlagd Sill", 9, 8, "24 - 250 g jars", 19.00, 0, 0, 20, 0),
    (37, "Gravad lax", 9, 8, "12 - 500 g pkgs.", 26.00, 0, 0, 25, 0),
    (38, "Côte de Blaye", 1, 1, "12 - 75 cl bottles", 263.50, 0, 0, 15, 0),
    (39, "Chartreuse verte", 1, 1, "750 cc per bottle", 18.00, 0, 0, 5, 0),
    (40, "Boston Crab Meat", 1, 8, "24 - 4 oz tins", 18.40, 0, 0, 30, 0),
    (41, "Jack's New England Clam Chowder", 1, 8, "12 - 12 oz cans", 9.65, 0, 0, 10, 0),
    (42, "Singaporean Hokkien Fried Mee", 6, 5, "32 - 1 kg pkgs.", 14.00, 0, 0, 0, 0),
    (43, "Ipoh Coffee", 6, 1, "16 - 500 g tins", 46.00, 0, 0, 25, 0),
    (44, "Gula Malacca", 6, 2, "20 - 2 kg bags", 19.45, 0, 0, 15, 0),
    (45, "Rogede sild", 9, 8, "1k pkg.", 9.50, 0, 0, 5, 0),
    (46, "Spegesild", 9, 8, "4 - 450 g glasses", 12.00, 0, 0, 10, 0),
    (47, "Zaanse koeken", 9, 3, "10 - 4 oz boxes", 9.50, 0, 0, 0, 0),
    (48, "Chocolade", 9, 3, "10 pkgs.", 12.75, 0, 0, 25, 0),
    (49, "Maxilaku", 7, 3, "24 - 50 g pkgs.", 20.00, 0, 0, 10, 0),
    (50, "Valkoinen suklaa", 7, 3, "12 - 100 g bars", 16.25, 0, 0, 0, 0),
]


def has_demo_data() -> bool:
    """Return True if any rows exist in transactional tables."""
    conn = get_connection()
    for table in ("DN", "INV", "GR", "SI", "SO", "CR", "CP", "BankEntry", "CN"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
        if count > 0:
            conn.close()
            return True
    conn.close()
    return False


def has_master_data() -> bool:
    """Return True if Categories table has any rows."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM Categories").fetchone()[0]
    conn.close()
    return count > 0


def demo_status() -> str:
    """Return a human-readable status string for the demo data state."""
    if has_demo_data():
        return "Demo data present"
    if has_master_data():
        return "Master data loaded"
    return "Clean (production-ready)"


# ── Private helpers ──────────────────────────────────────────────────────────


def _insert_additional_customers() -> None:
    """Insert 20 extra customers (total: 30)."""
    conn = get_connection()
    for c in _EXTRA_CUSTOMERS:
        conn.execute(
            "INSERT OR IGNORE INTO Customers VALUES (?,?,?,?,?,?,?,?,?,?,?)", c
        )
    conn.commit()
    conn.close()


def _insert_additional_suppliers() -> None:
    """Insert 5 extra suppliers (total: 15)."""
    conn = get_connection()
    for s in _EXTRA_SUPPLIERS:
        conn.execute(
            "INSERT OR IGNORE INTO Suppliers VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", s
        )
    conn.commit()
    conn.close()


def _insert_additional_products() -> None:
    """Insert 30 extra products (total: 50, initial stock: 0)."""
    conn = get_connection()
    for p in _EXTRA_PRODUCTS:
        conn.execute(
            "INSERT OR IGNORE INTO Products "
            "(ProductID,ProductName,SupplierID,CategoryID,QuantityPerUnit,"
            "UnitPrice,UnitsInStock,UnitsOnOrder,ReorderLevel,Discontinued) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)", p
        )
    conn.commit()
    conn.close()


def _build_pareto_weights(n: int, rng: random.Random) -> list[float]:
    """Build geometric weights so top 30% of items get ~60% of selections."""
    raw = [0.7 ** i for i in range(n)]
    total = sum(raw)
    return [w / total for w in raw]


def _weighted_choice(items: list, weights: list[float], rng: random.Random):
    """Pick one item using pre-computed weights."""
    r = rng.random()
    cumulative = 0.0
    for item, w in zip(items, weights):
        cumulative += w
        if r <= cumulative:
            return item
    return items[-1]


def _business_days(start: date, end: date):
    """Yield business days (Mon-Fri) from start to end inclusive."""
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def _generate_gr(rng, date_str, year, supplier_ids, product_catalog, stock,
                 counts):
    """Generate a single GR with 2-4 items, receive it, update stock tracker."""
    from data.gr import create_draft as gr_draft, add_item as gr_add, receive as gr_receive

    supplier_id = rng.choice(supplier_ids)
    # Pick products from this supplier preferably, else random
    supplier_products = [pid for pid, info in product_catalog.items()
                         if info["supplier_id"] == supplier_id]
    if len(supplier_products) < 2:
        supplier_products = list(product_catalog.keys())

    n_items = rng.randint(2, 4)
    chosen = rng.sample(supplier_products, min(n_items, len(supplier_products)))

    payment_method = rng.choice(["cash", "bank"])
    gr_id = gr_draft(supplier_id, date_str, supplier_doc_ref=f"SUP-{counts['GR']:04d}",
                     payment_method=payment_method, year_override=year)
    for pid in chosen:
        qty = rng.randint(12, 30)   # avg ≈ 21 units — buys ~190 units/day vs 160 sold
        cost = round(product_catalog[pid]["price"] * rng.uniform(0.5, 0.75), 2)
        gr_add(gr_id, pid, qty, cost)
        stock[pid] = stock.get(pid, 0) + qty
    gr_receive(gr_id, date_override=date_str)
    counts["GR"] += 1


def _generate_dn(rng, date_str, year, customer_id, product_catalog, stock,
                 issued_dns, counts):
    """Generate a single DN with 1-4 items, issue it, update stock tracker."""
    from data.dn import create_draft as dn_draft, add_item as dn_add, issue as dn_issue

    n_items = rng.randint(1, 4)
    available_pids = [pid for pid, s in stock.items() if s > 0]
    if not available_pids:
        return
    chosen = rng.sample(available_pids, min(n_items, len(available_pids)))

    dn_id = dn_draft(customer_id, date_str, year_override=year)
    items_added = 0
    for pid in chosen:
        max_qty = min(15, stock.get(pid, 0))
        if max_qty <= 0:
            continue
        qty = rng.randint(1, max_qty)
        price = product_catalog[pid]["price"]
        dn_add(dn_id, pid, qty, price)
        stock[pid] -= qty
        items_added += 1

    if items_added == 0:
        # Clean up empty draft
        conn = get_connection()
        conn.execute("DELETE FROM DN WHERE DN_ID=?", (dn_id,))
        conn.commit()
        conn.close()
        return

    dn_issue(dn_id)
    counts["DN"] += 1
    if customer_id not in issued_dns:
        issued_dns[customer_id] = []
    issued_dns[customer_id].append({"dn_id": dn_id, "date": date_str})


def _generate_invoices(rng, date_str, year, issued_dns, unpaid_invs, counts):
    """Batch 1-3 issued DNs per customer into invoices if old enough."""
    from data.inv import create as inv_create

    invoice_date = date.fromisoformat(date_str)
    for customer_id, dns in list(issued_dns.items()):
        # Invoice all eligible DNs in batches of 1-2
        while True:
            eligible = [d for d in dns
                        if (invoice_date - date.fromisoformat(d["date"])).days >= rng.randint(1, 3)]
            if not eligible:
                break
            batch_size = min(rng.randint(1, 2), len(eligible))
            batch = eligible[:batch_size]
            dn_ids = [d["dn_id"] for d in batch]

            payment_term = rng.choice([14, 30, 30, 30, 45, 60])
            method = rng.choice(["cash", "bank", "bank"])
            inv_id = inv_create(customer_id, dn_ids, date_str,
                                payment_term_days=payment_term,
                                payment_method=method,
                                year_override=year)
            counts["INV"] += 1

            # Remove invoiced DNs from queue
            for d in batch:
                dns.remove(d)

            # Track for payment
            due_date = str(invoice_date + timedelta(days=payment_term))
            if customer_id not in unpaid_invs:
                unpaid_invs[customer_id] = []
            unpaid_invs[customer_id].append({
                "inv_id": inv_id, "method": method,
                "due_date": due_date, "total": None,
                "customer_id": customer_id,
            })


def _process_payments(rng, date_str, year, unpaid_invs, counts):
    """Pay due/overdue invoices with realistic patterns."""
    from data.inv import record_payment

    current = date.fromisoformat(date_str)
    for customer_id, invs in list(unpaid_invs.items()):
        for inv_info in invs[:]:
            due = date.fromisoformat(inv_info["due_date"])
            days_until_due = (due - current).days

            # Check if it's time to pay
            if days_until_due > 5:
                continue  # not yet due

            # Decide payment behavior
            roll = rng.random()
            if roll < 0.05:
                # 5% never pay — remove from queue after 60 days overdue
                if days_until_due < -60:
                    invs.remove(inv_info)
                continue

            # Look up actual total
            conn = get_connection()
            row = conn.execute(
                "SELECT TotalNet, COALESCE(PaidAmount, 0) FROM INV WHERE INV_ID=?",
                (inv_info["inv_id"],),
            ).fetchone()
            conn.close()
            if not row:
                invs.remove(inv_info)
                continue
            total, paid_so_far = row[0] or 0, row[1]
            outstanding = total - paid_so_far
            if outstanding <= 0:
                invs.remove(inv_info)
                continue

            if roll < 0.15:
                # 10% late payment (+1 to 30 days)
                if days_until_due > -1:
                    continue
                amount = outstanding
            elif roll < 0.30:
                # 15% partial payment
                amount = round(outstanding * rng.uniform(0.5, 0.8), 2)
            else:
                # 70% full payment on/near due date
                amount = outstanding

            record_payment(inv_info["inv_id"], amount, inv_info["method"],
                           date_override=date_str)
            if amount >= outstanding:
                invs.remove(inv_info)
                counts["CR" if inv_info["method"] == "cash" else "BankEntry"] = \
                    counts.get("CR" if inv_info["method"] == "cash" else "BankEntry", 0) + 1


def _generate_credit_note(rng, date_str, year, counts):
    """Generate a CN on a random recent invoice."""
    from data.cn import create_partial_correction

    conn = get_connection()
    # Find a recent issued/paid invoice with items
    invs = conn.execute(
        "SELECT INV_ID FROM INV WHERE Status IN ('issued', 'paid', 'partial') "
        "ORDER BY INV_ID DESC LIMIT 20"
    ).fetchall()
    conn.close()
    if not invs:
        return

    inv_id = rng.choice(invs)[0]
    conn = get_connection()
    items = conn.execute(
        """SELECT p.ProductID, SUM(wi.Quantity) AS Qty, wi.UnitPrice
           FROM INV_DN fw
           JOIN DN_Items wi ON fw.DN_ID = wi.DN_ID
           JOIN Products p ON wi.ProductID = p.ProductID
           WHERE fw.INV_ID = ?
           GROUP BY p.ProductID, wi.UnitPrice""",
        (inv_id,),
    ).fetchall()
    conn.close()
    if not items:
        return

    # Pick 1-2 items for correction
    n_corr = min(rng.randint(1, 2), len(items))
    chosen_items = rng.sample(list(items), n_corr)

    corrections = []
    for it in chosen_items:
        orig_qty = it[1]
        new_qty = max(0, orig_qty - rng.randint(1, max(1, orig_qty)))
        corrections.append({
            "product_id": it[0],
            "new_quantity": new_qty,
            "new_unit_price": it[2],
        })

    reasons = [
        "Damaged goods on delivery", "Wrong product shipped",
        "Quantity discrepancy", "Quality issue reported by customer",
        "Price correction", "Returned items",
    ]
    create_partial_correction(
        inv_id=inv_id, reason=rng.choice(reasons),
        cn_date=date_str, user_id=1, corrections=corrections,
        reverse_stock=True, year_override=year,
    )
    counts["CN"] += 1


def _generate_stock_adjustment(rng, date_str, year, stock, product_catalog,
                               counts):
    """Generate an SI or SO stock adjustment."""
    from data.si_so import create_si, create_so

    if rng.random() < 0.5:
        # SI: surplus found
        n_items = rng.randint(1, 3)
        pids = rng.sample(list(product_catalog.keys()), min(n_items, len(product_catalog)))
        items = []
        for pid in pids:
            qty = rng.randint(5, 25)
            items.append({"product_id": pid, "quantity": qty})
            stock[pid] = stock.get(pid, 0) + qty
        create_si(date_str, reason=rng.choice(_SI_REASONS),
                  items=items, year_override=year)
        counts["SI"] += 1
    else:
        # SO: damaged/samples
        available = [pid for pid, s in stock.items() if s >= 10]
        if not available:
            return
        n_items = rng.randint(1, 2)
        pids = rng.sample(available, min(n_items, len(available)))
        items = []
        for pid in pids:
            qty = rng.randint(2, min(10, stock[pid]))
            items.append({"product_id": pid, "quantity": qty})
            stock[pid] -= qty
        reasons = ["Damaged goods write-off", "Free samples", "Expired stock",
                   "Quality control rejection"]
        create_so(date_str, reason=rng.choice(reasons),
                  items=items, year_override=year)
        counts["SO"] += 1


def _generate_transfer(rng, date_str, counts):
    """Transfer cash to bank."""
    from data.cash import transfer_to_bank, get_cash_balance

    amount = round(rng.uniform(500, 5000), 2)
    balance = get_cash_balance()
    if balance <= 0:
        return  # nothing to sweep
    amount = min(amount, balance)
    date_obj = date.fromisoformat(date_str)
    desc = (
        "Monthly cash sweep — mid-month"
        if date_obj.day == 15
        else "Monthly cash sweep — start of month"
    )
    transfer_to_bank(amount, desc, date_override=date_str)
    counts["transfers"] += 1


# ── Main public API ──────────────────────────────────────────────────────────


def insert_demo_data() -> dict:
    """Create a large-scale realistic demo scenario spanning Jan 2025 – Feb 2026.

    Seeds master data (via db.seed_data) if absent, expands to 30 customers,
    15 suppliers, 50 products, then generates thousands of transactional
    documents with realistic distributions and seasonality.

    Deterministic: uses random.Random(seed=42) for reproducible output.

    Raises ValueError if transactional data already exists.
    Returns summary dict with counts per document type + elapsed_seconds.
    """
    if has_demo_data():
        raise ValueError(
            "Transactional data already exists. Clean first."
        )

    t0 = time.time()
    rng = random.Random(42)

    from data.settings import set_setting
    set_setting("production_mode", "false")

    import db
    db.seed_data()  # idempotent — only seeds if Categories is empty

    # Opening working capital: initial bank deposit at business start
    from data.bank import create_bank_entry as _create_opening_entry
    _create_opening_entry(
        direction="in",
        amount=150_000.00,
        description="Opening capital — initial working capital deposit",
        date_override="2025-01-01",
    )

    # Phase 0: Expand master data
    _insert_additional_customers()
    _insert_additional_suppliers()
    _insert_additional_products()

    # Build in-memory structures
    conn = get_connection()
    customer_ids = [r[0] for r in conn.execute("SELECT CustomerID FROM Customers").fetchall()]
    supplier_ids = [r[0] for r in conn.execute("SELECT SupplierID FROM Suppliers").fetchall()]

    product_catalog = {}
    stock = {}
    for r in conn.execute(
        "SELECT ProductID, UnitPrice, SupplierID, CategoryID, UnitsInStock, Discontinued "
        "FROM Products"
    ).fetchall():
        if r[5]:  # skip discontinued
            continue
        product_catalog[r[0]] = {
            "price": r[1], "supplier_id": r[2], "category_id": r[3],
        }
        stock[r[0]] = r[4]
    conn.close()

    # Shuffle customer list for Pareto weighting
    rng.shuffle(customer_ids)
    customer_weights = _build_pareto_weights(len(customer_ids), rng)

    counts: dict[str, int] = {
        "DN": 0, "INV": 0, "GR": 0, "CN": 0,
        "SI": 0, "SO": 0, "CR": 0, "CP": 0,
        "BankEntry": 0, "transfers": 0,
    }

    issued_dns: dict[str, list] = {}   # customer_id → [{"dn_id", "date"}]
    unpaid_invs: dict[str, list] = {}  # customer_id → [inv_info dicts]

    start_date = date(2025, 1, 1)
    end_date = date(2026, 2, 1)

    # Phase 1: Day-by-day generation
    for day in _business_days(start_date, end_date):
        date_str = str(day)
        year = day.year
        month = day.month
        mult = _SEASONALITY.get((year, month), 1.0)

        # 1. GRs first (restock)
        n_grs = max(1, int(3 * mult + rng.uniform(-0.5, 0.5)))
        # Emergency restock: if >40% of products below 20 units
        low_stock_count = sum(1 for s in stock.values() if s < 20)
        if low_stock_count > len(stock) * 0.4:
            n_grs += 2

        for _ in range(n_grs):
            _generate_gr(rng, date_str, year, supplier_ids, product_catalog,
                         stock, counts)

        # 2. DNs (deliveries)
        n_dns = max(1, int(8 * mult + rng.uniform(-1, 1)))
        for _ in range(n_dns):
            customer_id = _weighted_choice(customer_ids, customer_weights, rng)
            _generate_dn(rng, date_str, year, customer_id, product_catalog,
                         stock, issued_dns, counts)

        # 3. Invoicing — batch issued DNs
        _generate_invoices(rng, date_str, year, issued_dns, unpaid_invs, counts)

        # 4. Payments
        _process_payments(rng, date_str, year, unpaid_invs, counts)

        # 5. Credit Notes (~18% of days → ~50 total)
        if rng.random() < 0.18:
            _generate_credit_note(rng, date_str, year, counts)

        # 6. Stock adjustments (~22% of days → ~60 SI+SO total)
        if rng.random() < 0.22:
            _generate_stock_adjustment(rng, date_str, year, stock,
                                       product_catalog, counts)

        # 7. Transfers on 1st and 15th
        if day.day in (1, 15):
            _generate_transfer(rng, date_str, counts)

    # Post-loop: collect outstanding AR from invoices whose due dates fall after loop end
    for day in _business_days(date(2026, 2, 2), date(2026, 4, 30)):
        _process_payments(rng, str(day), day.year, unpaid_invs, counts)

    # Final: read actual DB counts for auto-generated docs (CP, CR, BankEntry)
    conn = get_connection()
    for table in ("DN", "INV", "GR", "CN", "SI", "SO", "CR", "CP", "BankEntry"):
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
    conn.close()

    elapsed = round(time.time() - t0, 1)
    counts["elapsed_seconds"] = elapsed
    return counts


def clean_demo_data() -> dict:
    """Delete ALL data except AppUsers and AppSettings (FK-safe order).

    Sets production_mode flag to prevent init_db() from re-seeding.
    Returns summary with deleted row counts.
    """
    conn = get_connection()
    deleted: dict[str, int] = {}

    # Phase 1: transactional tables
    for table in _TRANSACTIONAL_TABLES:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
        conn.execute(f"DELETE FROM {table}")  # noqa: S608
        deleted[table] = count

    # Phase 2: master tables — nullify Employees self-FK first
    conn.execute("UPDATE Employees SET ReportsTo = NULL")

    for table in _MASTER_TABLES:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
        conn.execute(f"DELETE FROM {table}")  # noqa: S608
        deleted[table] = count

    conn.commit()
    conn.close()

    # Set production mode to prevent auto-reseeding
    from data.settings import set_setting
    set_setting("production_mode", "true")

    return deleted
