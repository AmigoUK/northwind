from __future__ import annotations
"""screens/reconciliation.py — AR/AP Reconciliation panel."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static
from textual import on

import data.reconciliation as rdata
import data.customers as cdata
import data.suppliers as sdata
import data.inv as inv_data
from data.settings import get_currency_symbol
from screens.modals import PickerModal


class AllocateToINVModal(ModalScreen[bool]):
    """Pick an open INV for the customer and allocate an unallocated CR or BankEntry to it."""

    def __init__(
        self,
        doc_type: str,
        doc_id: int,
        amount: float,
        customer_id: str,
    ) -> None:
        super().__init__()
        self._doc_type = doc_type
        self._doc_id = doc_id
        self._amount = amount
        self._customer_id = customer_id

    def compose(self) -> ComposeResult:
        sym = get_currency_symbol()
        doc_label = self._doc_type.upper()
        with Vertical(classes="modal-dialog"):
            yield Label("Allocate Payment to Invoice", classes="modal-title")
            yield Label(
                f"Payment: {doc_label} #{self._doc_id}   Amount: {sym}{self._amount:.2f}",
                classes="modal-subtitle",
            )
            yield DataTable(id="inv-tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="modal-buttons"):
                yield Button("Allocate", id="btn-allocate", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        from db import get_connection
        tbl = self.query_one("#inv-tbl", DataTable)
        for label, width in [
            ("ID", 6), ("Number", 18), ("Date", 12), ("Due Date", 12),
            ("Total", 10), ("Paid", 10), ("Outstanding", 12),
        ]:
            tbl.add_column(label, width=width)

        conn = get_connection()
        rows = conn.execute(
            """SELECT INV_ID, INV_Number, INV_Date, DueDate,
                      TotalNet, COALESCE(PaidAmount, 0),
                      TotalNet - COALESCE(PaidAmount, 0) AS Outstanding
               FROM INV
               WHERE CustomerID=? AND Status IN ('issued','partial')
               ORDER BY INV_Date""",
            (self._customer_id,),
        ).fetchall()
        conn.close()

        sym = get_currency_symbol()
        for row in rows:
            inv_id, number, date, due, total, paid, outstanding = row
            tbl.add_row(
                str(inv_id), number, date or "", due or "",
                f"{sym}{total:.2f}", f"{sym}{paid:.2f}", f"{sym}{outstanding:.2f}",
                key=str(inv_id),
            )

    @on(Button.Pressed, "#btn-allocate")
    def on_allocate(self) -> None:
        tbl = self.query_one("#inv-tbl", DataTable)
        if tbl.row_count == 0:
            self.notify("No open invoices to allocate to.", severity="warning")
            return
        try:
            inv_id_str = tbl.coordinate_to_cell_key(tbl.cursor_coordinate).row_key.value
        except Exception:
            self.notify("Select an invoice first.", severity="warning")
            return
        if inv_id_str is None:
            self.notify("Select an invoice first.", severity="warning")
            return
        try:
            rdata.allocate_payment_to_inv(self._doc_type, self._doc_id, int(inv_id_str))
            self.notify("Payment allocated successfully.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Allocation failed: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class AllocateToGRModal(ModalScreen[bool]):
    """Pick a received GR for the supplier and allocate an unallocated CP or BankEntry to it."""

    def __init__(
        self,
        doc_type: str,
        doc_id: int,
        amount: float,
        supplier_id: int,
    ) -> None:
        super().__init__()
        self._doc_type = doc_type
        self._doc_id = doc_id
        self._amount = amount
        self._supplier_id = supplier_id

    def compose(self) -> ComposeResult:
        sym = get_currency_symbol()
        doc_label = self._doc_type.upper()
        with Vertical(classes="modal-dialog"):
            yield Label("Allocate Payment to Goods Receipt", classes="modal-title")
            yield Label(
                f"Payment: {doc_label} #{self._doc_id}   Amount: {sym}{self._amount:.2f}",
                classes="modal-subtitle",
            )
            yield DataTable(id="gr-tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="modal-buttons"):
                yield Button("Allocate", id="btn-allocate", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        from db import get_connection
        tbl = self.query_one("#gr-tbl", DataTable)
        for label, width in [
            ("ID", 6), ("Number", 18), ("Date", 12), ("Total Cost", 14),
        ]:
            tbl.add_column(label, width=width)

        conn = get_connection()
        rows = conn.execute(
            """SELECT g.GR_ID, g.GR_Number, g.GR_Date,
                      COALESCE(SUM(gi.Quantity * gi.UnitCost), 0) AS TotalCost
               FROM GR g
               LEFT JOIN GR_Items gi ON g.GR_ID = gi.GR_ID
               WHERE g.SupplierID=? AND g.Status='received'
               GROUP BY g.GR_ID
               ORDER BY g.GR_Date""",
            (self._supplier_id,),
        ).fetchall()
        conn.close()

        sym = get_currency_symbol()
        for row in rows:
            gr_id, number, date, total_cost = row
            tbl.add_row(
                str(gr_id), number, date or "", f"{sym}{total_cost:.2f}",
                key=str(gr_id),
            )

    @on(Button.Pressed, "#btn-allocate")
    def on_allocate(self) -> None:
        tbl = self.query_one("#gr-tbl", DataTable)
        if tbl.row_count == 0:
            self.notify("No received GRs to allocate to.", severity="warning")
            return
        try:
            gr_id_str = tbl.coordinate_to_cell_key(tbl.cursor_coordinate).row_key.value
        except Exception:
            self.notify("Select a GR first.", severity="warning")
            return
        if gr_id_str is None:
            self.notify("Select a GR first.", severity="warning")
            return
        try:
            rdata.allocate_payment_to_gr(self._doc_type, self._doc_id, int(gr_id_str))
            self.notify("Payment allocated successfully.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Allocation failed: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class PayInvoiceModal(ModalScreen[bool]):
    """Register a payment against an open INV."""

    def __init__(self, inv_id: int, inv_number: str, customer_id: str) -> None:
        super().__init__()
        self._inv_id = inv_id
        self._inv_number = inv_number
        self._customer_id = customer_id
        self._outstanding: float = 0.0

    def compose(self) -> ComposeResult:
        sym = get_currency_symbol()
        with Vertical(classes="modal-dialog"):
            yield Label(f"Register Payment — {self._inv_number}", classes="modal-title")
            yield Label("", id="lbl-outstanding", classes="modal-subtitle")
            with Horizontal(classes="modal-row"):
                yield Label("Amount:")
                yield Input(id="inp-amount", placeholder="0.00")
            with Horizontal(classes="modal-row"):
                yield Label("Method:")
                yield Select(
                    [("Cash (CR)", "cash"), ("Bank Transfer", "bank")],
                    id="sel-method",
                    value="cash",
                )
            with Horizontal(classes="modal-row"):
                yield Label("Description:")
                yield Input(id="inp-desc", placeholder="(optional)")
            with Horizontal(classes="modal-buttons"):
                yield Button("Register Payment", id="btn-pay", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        inv = inv_data.get_by_pk(self._inv_id)
        if inv:
            self._outstanding = float(inv.get("Outstanding", 0) or 0)
        sym = get_currency_symbol()
        self.query_one("#lbl-outstanding", Label).update(
            f"Outstanding: {sym}{self._outstanding:.2f}"
        )
        self.query_one("#inp-amount", Input).value = f"{self._outstanding:.2f}"

    @on(Button.Pressed, "#btn-pay")
    def on_pay(self) -> None:
        amount_str = self.query_one("#inp-amount", Input).value.strip()
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self.notify("Enter a valid positive amount.", severity="warning")
            return
        method = self.query_one("#sel-method", Select).value
        desc = self.query_one("#inp-desc", Input).value.strip()
        try:
            inv_data.record_payment(self._inv_id, amount, method, desc)
            self.notify("Payment registered successfully.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Payment failed: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class ReconciliationPanel(Widget):
    """AR/AP Reconciliation panel — account statements, aging, and payment allocation."""

    BINDINGS = [
        Binding("a", "allocate",       "Allocate Payment"),
        Binding("p", "pay_invoice",    "Pay Invoice"),
        Binding("r", "refresh",        "Refresh"),
        Binding("u", "sub_unpaid",     "All Unpaid"),
        Binding("s", "sub_statement",  "Statement"),
    ]

    _mode: str = "ar"          # "ar" or "ap"
    _sub_view: str = "unpaid"  # "unpaid" | "statement"
    _entity_id = None          # CustomerID (str) or SupplierID (int) or None
    _entity_name: str = ""
    _row_meta: dict            # key -> {doc_type, doc_id, allocated, entity_id, amount}
    _unpaid_meta: dict         # key -> {doc_type, doc_id, customer_id/supplier_id, outstanding}

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._row_meta = {}
        self._unpaid_meta = {}

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            with Horizontal(classes="toolbar"):
                yield Button("AR — Customer",  id="btn-ar",        variant="primary")
                yield Button("AP — Supplier",  id="btn-ap")
                yield Button("All Unpaid",     id="btn-unpaid",    variant="primary")
                yield Button("Statement",      id="btn-statement")
                yield Button("▼ Filter",       id="btn-pick")
                yield Button("✕ Clear",        id="btn-clear")
                yield Label("(all)", id="lbl-entity")
            yield Static("", id="lbl-summary")
            yield DataTable(id="tbl-unpaid",   cursor_type="row", zebra_stripes=True)
            yield DataTable(id="tbl-statement", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("Allocate",    id="btn-allocate",  variant="primary")
                yield Button("Pay Invoice", id="btn-pay-inv")
                yield Button("Refresh",     id="btn-refresh")
            yield Static("", id="lbl-aging")

    def on_mount(self) -> None:
        # Statement table columns (unchanged from previous version)
        stmt = self.query_one("#tbl-statement", DataTable)
        for label, width in [
            ("Date", 12), ("Type", 8), ("Document", 18), ("Description", 24),
            ("Debit", 12), ("Credit", 12), ("Balance", 12),
        ]:
            stmt.add_column(label, width=width)

        # Unpaid table — generic columns work for both AR and AP
        self._setup_unpaid_columns()

        # Start on Unpaid sub-view
        self.query_one("#tbl-statement", DataTable).display = False
        self.query_one("#btn-allocate",  Button).display = False
        self._refresh_unpaid()

    def _setup_unpaid_columns(self) -> None:
        tbl = self.query_one("#tbl-unpaid", DataTable)
        for label, width in [
            ("Entity", 22), ("Date", 12), ("Document", 16), ("Due", 12),
            ("Total", 10), ("Outstanding", 12), ("Overdue", 8), ("Status", 10),
        ]:
            tbl.add_column(label, width=width)

    # ── Mode toggle ────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-ar")
    def on_ar_mode(self) -> None:
        if self._mode == "ar":
            return
        self._mode = "ar"
        self._entity_id = None
        self._entity_name = ""
        self.query_one("#btn-ar", Button).variant = "primary"
        self.query_one("#btn-ap", Button).variant = "default"
        self.query_one("#lbl-entity", Label).update("(all)")
        self.query_one("#btn-pay-inv", Button).display = True
        self.query_one("#lbl-summary", Static).update("")
        if self._sub_view == "unpaid":
            self._refresh_unpaid()
        else:
            self._clear_table()
            self._refresh_aging()

    @on(Button.Pressed, "#btn-ap")
    def on_ap_mode(self) -> None:
        if self._mode == "ap":
            return
        self._mode = "ap"
        self._entity_id = None
        self._entity_name = ""
        self.query_one("#btn-ar", Button).variant = "default"
        self.query_one("#btn-ap", Button).variant = "primary"
        self.query_one("#lbl-entity", Label).update("(all)")
        self.query_one("#btn-pay-inv", Button).display = False
        self.query_one("#lbl-summary", Static).update("")
        self.query_one("#lbl-aging", Static).update("")
        if self._sub_view == "unpaid":
            self._refresh_unpaid()
        else:
            self._clear_table()

    # ── Sub-view toggle ────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-unpaid")
    def on_btn_unpaid(self) -> None:
        self.action_sub_unpaid()

    @on(Button.Pressed, "#btn-statement")
    def on_btn_statement(self) -> None:
        self.action_sub_statement()

    def action_sub_unpaid(self) -> None:
        if self._sub_view == "unpaid":
            return
        self._sub_view = "unpaid"
        self.query_one("#btn-unpaid",    Button).variant = "primary"
        self.query_one("#btn-statement", Button).variant = "default"
        self.query_one("#tbl-unpaid",    DataTable).display = True
        self.query_one("#tbl-statement", DataTable).display = False
        self.query_one("#btn-allocate",  Button).display = False
        self.query_one("#btn-pick",      Button).label = "▼ Filter"
        self._refresh_unpaid()

    def action_sub_statement(self) -> None:
        if self._sub_view == "statement":
            return
        self._sub_view = "statement"
        self.query_one("#btn-unpaid",    Button).variant = "default"
        self.query_one("#btn-statement", Button).variant = "primary"
        self.query_one("#tbl-unpaid",    DataTable).display = False
        self.query_one("#tbl-statement", DataTable).display = True
        self.query_one("#btn-allocate",  Button).display = True
        self.query_one("#btn-pick",      Button).label = "▼ Pick"
        self.refresh_statement()

    # ── Entity picker ──────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-pick")
    def on_pick(self) -> None:
        if self._mode == "ar":
            rows = cdata.fetch_for_picker()
            self.app.push_screen(
                PickerModal(
                    "Select Customer",
                    [("ID", 6), ("Company", 26), ("Contact", 18), ("City", 12)],
                    rows,
                    pk_col=0,
                ),
                callback=self._after_pick_customer,
            )
        else:
            rows = sdata.fetch_for_picker()
            self.app.push_screen(
                PickerModal(
                    "Select Supplier",
                    [("ID", 4), ("Company", 26), ("City", 14), ("Country", 12)],
                    rows,
                    pk_col=0,
                ),
                callback=self._after_pick_supplier,
            )

    @on(Button.Pressed, "#btn-clear")
    def on_btn_clear(self) -> None:
        self._entity_id = None
        self._entity_name = ""
        self.query_one("#lbl-entity", Label).update("(all)")
        if self._sub_view == "unpaid":
            self._refresh_unpaid()
        else:
            self._clear_table()
            self.query_one("#lbl-summary", Static).update("")

    def _after_pick_customer(self, pk: str | None) -> None:
        if not pk:
            return
        self._entity_id = pk
        cust = cdata.get_by_pk(pk)
        self._entity_name = cust["CompanyName"] if cust else pk
        self.query_one("#lbl-entity", Label).update(f"{pk} — {self._entity_name}")
        if self._sub_view == "unpaid":
            self._refresh_unpaid()
        else:
            self.refresh_statement()

    def _after_pick_supplier(self, pk: str | None) -> None:
        if not pk:
            return
        self._entity_id = int(pk)
        sup = sdata.get_by_pk(int(pk))
        self._entity_name = sup["CompanyName"] if sup else pk
        self.query_one("#lbl-entity", Label).update(f"{pk} — {self._entity_name}")
        if self._sub_view == "unpaid":
            self._refresh_unpaid()
        else:
            self.refresh_statement()

    # ── Unpaid view refresh ────────────────────────────────────────────────────

    def _refresh_unpaid(self) -> None:
        tbl = self.query_one("#tbl-unpaid", DataTable)
        tbl.clear()
        self._unpaid_meta = {}
        sym = get_currency_symbol()

        if self._mode == "ar":
            rows = rdata.fetch_all_unpaid_inv(
                str(self._entity_id) if self._entity_id else None
            )
            total_outstanding = sum(r["outstanding"] for r in rows)
            customer_count = len({r["customer_id"] for r in rows})
            for i, r in enumerate(rows):
                key = f"inv:{r['inv_id']}:{i}"
                overdue = r["days_overdue"]
                tbl.add_row(
                    r["customer_name"],
                    r["date"] or "",
                    r["inv_number"],
                    r["due_date"] or "—",
                    f"{sym}{r['total']:.2f}",
                    f"{sym}{r['outstanding']:.2f}",
                    f"{overdue}d" if overdue > 0 else "—",
                    r["status"],
                    key=key,
                )
                self._unpaid_meta[key] = {
                    "doc_type":    "inv",
                    "doc_id":      r["inv_id"],
                    "customer_id": r["customer_id"],
                    "outstanding": r["outstanding"],
                }
            filter_note = f"  (filter: {self._entity_name})" if self._entity_id else ""
            self.query_one("#lbl-summary", Static).update(
                f"Unpaid Invoices: {len(rows)}  |  "
                f"Total outstanding: {sym}{total_outstanding:.2f}  |  "
                f"Customers: {customer_count}{filter_note}"
            )
            self._refresh_aging()

        else:  # AP
            rows = rdata.fetch_all_unpaid_gr(
                int(self._entity_id) if self._entity_id else None
            )
            total_cost = sum(r["total_cost"] for r in rows)
            supplier_count = len({r["supplier_id"] for r in rows})
            for i, r in enumerate(rows):
                key = f"gr:{r['gr_id']}:{i}"
                tbl.add_row(
                    r["supplier_name"],
                    r["date"] or "",
                    r["gr_number"],
                    "—",
                    f"{sym}{r['total_cost']:.2f}",
                    f"{sym}{r['total_cost']:.2f}",
                    "—",
                    "received",
                    key=key,
                )
                self._unpaid_meta[key] = {
                    "doc_type":    "gr",
                    "doc_id":      r["gr_id"],
                    "supplier_id": r["supplier_id"],
                    "outstanding": r["total_cost"],
                }
            filter_note = f"  (filter: {self._entity_name})" if self._entity_id else ""
            self.query_one("#lbl-summary", Static).update(
                f"Unpaid GRs: {len(rows)}  |  "
                f"Total payable: {sym}{total_cost:.2f}  |  "
                f"Suppliers: {supplier_count}{filter_note}"
            )

    # ── Statement refresh ──────────────────────────────────────────────────────

    def refresh_statement(self) -> None:
        if self._entity_id is None:
            self._clear_table()
            self.query_one("#lbl-summary", Static).update("")
            return

        if self._mode == "ar":
            rows = rdata.fetch_customer_statement(str(self._entity_id))
        else:
            rows = rdata.fetch_supplier_statement(int(self._entity_id))

        self._populate_table(rows)
        self._update_summary(rows)
        if self._mode == "ar":
            self._refresh_aging()

    def _clear_table(self) -> None:
        tbl = self.query_one("#tbl-statement", DataTable)
        tbl.clear()
        self._row_meta = {}

    def _populate_table(self, rows: list[dict]) -> None:
        tbl = self.query_one("#tbl-statement", DataTable)
        tbl.clear()
        self._row_meta = {}
        sym = get_currency_symbol()

        for i, row in enumerate(rows):
            doc_type = row["doc_type"]
            allocated = row["allocated"]
            prefix = "" if allocated else ""
            type_cell = f"{prefix}{doc_type}"

            debit_str  = f"{sym}{row['debit']:.2f}"  if row["debit"]  > 0 else ""
            credit_str = f"{sym}{row['credit']:.2f}" if row["credit"] > 0 else ""
            bal = row["balance"]
            bal_str = f"{sym}{abs(bal):.2f}" + (" CR" if bal < 0 else " DR" if bal > 0 else "")

            key = f"{doc_type}:{row['doc_id']}:{i}"
            tbl.add_row(
                row["date"] or "",
                type_cell,
                row["doc_number"] or "",
                row["description"] or "",
                debit_str,
                credit_str,
                bal_str,
                key=key,
            )
            self._row_meta[key] = {
                "doc_type":  doc_type.lower(),
                "doc_id":    row["doc_id"],
                "allocated": allocated,
                "amount":    row["credit"] if row["credit"] > 0 else row["debit"],
            }

    def _update_summary(self, rows: list[dict]) -> None:
        sym = get_currency_symbol()
        balance = rows[-1]["balance"] if rows else 0.0
        open_items = sum(
            1 for r in rows
            if r["doc_type"] in ("INV", "GR") or not r["allocated"]
        )
        unalloc = sum(1 for r in rows if not r["allocated"])
        self.query_one("#lbl-summary", Static).update(
            f"Balance: {sym}{abs(balance):.2f}"
            f"{'  (credit)' if balance < 0 else '  (debit)' if balance > 0 else ''}"
            f"   Open items: {open_items}   Unallocated: {unalloc}"
        )

    def _refresh_aging(self) -> None:
        aging_bar = self.query_one("#lbl-aging", Static)
        try:
            sym = get_currency_symbol()
            rows = rdata.fetch_ar_aging()
            if not rows:
                aging_bar.update("AR Aging: no overdue items")
                return
            totals = {
                "current": sum(r["current_amt"] for r in rows),
                "1-30":    sum(r["d1_30"]       for r in rows),
                "31-60":   sum(r["d31_60"]      for r in rows),
                "61-90":   sum(r["d61_90"]      for r in rows),
                "90+":     sum(r["d90plus"]     for r in rows),
            }
            parts = [
                f"AR Aging:",
                f"Not Due {sym}{totals['current']:.0f}",
                f"1-30d {sym}{totals['1-30']:.0f}",
                f"31-60d {sym}{totals['31-60']:.0f}",
                f"61-90d {sym}{totals['61-90']:.0f}",
                f"90+d {sym}{totals['90+']:.0f}",
            ]
            aging_bar.update("  |  ".join(parts))
        except Exception:
            aging_bar.update("")

    # ── Toolbar buttons ────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-allocate")
    def on_btn_allocate(self) -> None:
        self.action_allocate()

    @on(Button.Pressed, "#btn-pay-inv")
    def on_btn_pay_inv(self) -> None:
        self.action_pay_invoice()

    @on(Button.Pressed, "#btn-refresh")
    def on_btn_refresh(self) -> None:
        self.action_refresh()

    # ── Actions ────────────────────────────────────────────────────────────────

    def action_allocate(self) -> None:
        if self._entity_id is None:
            self.notify("Select an entity first.", severity="warning")
            return

        tbl = self.query_one("#tbl-statement", DataTable)
        if tbl.row_count == 0:
            self.notify("No rows to allocate.", severity="warning")
            return

        try:
            key = tbl.coordinate_to_cell_key(tbl.cursor_coordinate).row_key.value
        except Exception:
            self.notify("Select a row first.", severity="warning")
            return

        meta = self._row_meta.get(key)
        if not meta:
            self.notify("Select a row first.", severity="warning")
            return

        doc_type = meta["doc_type"]
        doc_id = meta["doc_id"]
        amount = meta["amount"]

        if self._mode == "ar":
            if doc_type == "inv":
                self.notify(
                    "Select an unallocated CR or BankIN row to link to an invoice. "
                    "To register a new payment, use Pay Invoice.",
                    severity="warning",
                )
                return
            if doc_type not in ("cr", "bankin"):
                self.notify("This row type cannot be allocated.", severity="warning")
                return
            if meta["allocated"]:
                self.notify("This payment is already linked to an invoice.", severity="warning")
                return
            actual_doc_type = "cr" if doc_type == "cr" else "bank"
            self.app.push_screen(
                AllocateToINVModal(actual_doc_type, doc_id, amount, str(self._entity_id)),
                callback=self._after_allocate,
            )
        else:
            if doc_type == "gr":
                self.notify(
                    "Select an unallocated CP or BankOUT row to link to a GR.",
                    severity="warning",
                )
                return
            if doc_type not in ("cp", "bankout"):
                self.notify("This row type cannot be allocated.", severity="warning")
                return
            if meta["allocated"]:
                self.notify("This payment is already linked to an invoice.", severity="warning")
                return
            actual_doc_type = "cp" if doc_type == "cp" else "bank"
            self.app.push_screen(
                AllocateToGRModal(actual_doc_type, doc_id, amount, int(self._entity_id)),
                callback=self._after_allocate,
            )

    def _after_allocate(self, result: bool) -> None:
        if result:
            self.refresh_statement()  # allocate only works in statement view

    def action_pay_invoice(self) -> None:
        if self._mode != "ar":
            return
        if self._sub_view == "unpaid":
            tbl = self.query_one("#tbl-unpaid", DataTable)
            meta_dict = self._unpaid_meta
        else:
            tbl = self.query_one("#tbl-statement", DataTable)
            meta_dict = self._row_meta
            if self._entity_id is None:
                self.notify("Select a customer first.", severity="warning")
                return
        if tbl.row_count == 0:
            self.notify("No rows in view.", severity="warning")
            return
        try:
            key = tbl.coordinate_to_cell_key(tbl.cursor_coordinate).row_key.value
        except Exception:
            self.notify("Select an invoice row first.", severity="warning")
            return
        meta = meta_dict.get(key)
        if not meta or meta["doc_type"] != "inv":
            self.notify("Select an invoice (INV) row to register a payment.", severity="warning")
            return
        inv_id = meta["doc_id"]
        from db import get_connection
        conn = get_connection()
        row = conn.execute("SELECT INV_Number FROM INV WHERE INV_ID=?", (inv_id,)).fetchone()
        conn.close()
        inv_number = row[0] if row else f"INV #{inv_id}"
        cust_id = meta.get("customer_id") or str(self._entity_id)
        self.app.push_screen(
            PayInvoiceModal(inv_id, inv_number, cust_id),
            callback=self._after_pay_invoice,
        )

    def _after_pay_invoice(self, result: bool) -> None:
        if result:
            if self._sub_view == "unpaid":
                self._refresh_unpaid()
            else:
                self.refresh_statement()

    def action_refresh(self) -> None:
        if self._sub_view == "unpaid":
            self._refresh_unpaid()
        else:
            self.refresh_statement()
            if self._mode == "ar":
                self._refresh_aging()

    def refresh_data(self) -> None:
        if self._sub_view == "unpaid":
            self._refresh_unpaid()
        else:
            self.refresh_statement()
            if self._mode == "ar":
                self._refresh_aging()
