from __future__ import annotations
"""screens/inv.py — INV (Invoice) panel, detail, and creation flow."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static
from textual import on

import data.inv as invdata
import data.customers as cdata
import data.dn as dndata
from data.settings import get_currency_symbol
from data.users import has_permission
from screens.modals import ConfirmDeleteModal, CancellationReasonModal, PickerModal


class INVNewModal(ModalScreen):
    """Multi-step modal to create a new INV invoice."""

    def __init__(self) -> None:
        super().__init__()
        self._customer_id = None
        self._customer_name = ""
        self._selected_dn_ids: set[int] = set()

    def compose(self) -> ComposeResult:
        with Vertical(classes="order-detail-dialog"):
            yield Label("New INV — Invoice", classes="modal-title")
            yield Label("Customer *:")
            with Horizontal():
                yield Label("(none)", id="lbl-customer")
                yield Button("Pick Customer", id="btn-pick-cust")
            yield Label("Available DN (issued, not invoiced):", classes="section-label")
            yield DataTable(id="dn-tbl", cursor_type="row", zebra_stripes=True)
            yield Static("", id="dn-hint")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("INV Date (YYYY-MM-DD) *:")
                    yield Input(id="f-invdate", placeholder="2026-01-01")
                with Vertical(classes="form-field"):
                    yield Label("Payment Terms:")
                    yield Select(
                        [
                            ("Immediate (0 days)", 0),
                            ("14 days", 14),
                            ("30 days", 30),
                            ("60 days", 60),
                            ("90 days", 90),
                        ],
                        id="f-terms", value=30,
                    )
                with Vertical(classes="form-field"):
                    yield Label("Preferred Payment Method:")
                    yield Select(
                        [("bank", "bank"), ("cash", "cash"), ("(none)", "(none)")],
                        id="f-payment", value="bank",
                    )
            yield Static("", id="lbl-due")
            yield Label("Notes:")
            yield Input(id="f-notes", placeholder="Optional notes")
            with Horizontal(classes="modal-buttons"):
                yield Button("Create Invoice", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("Space=toggle DN selection  ESC=close", classes="modal-hint")

    def on_mount(self) -> None:
        from datetime import date
        self.query_one("#f-invdate", Input).value = str(date.today())
        tbl = self.query_one("#dn-tbl", DataTable)
        for label, width in [
            ("Sel", 4), ("DN_ID", 6), ("Number", 20), ("Date", 12), ("Total", 12),
        ]:
            tbl.add_column(label, width=width)
        self._update_due_label()

    def _update_due_label(self) -> None:
        from datetime import date, timedelta
        inv_date_str = self.query_one("#f-invdate", Input).value.strip()
        terms = self.query_one("#f-terms", Select).value
        try:
            inv_date = date.fromisoformat(inv_date_str)
            days = int(terms) if terms != Select.BLANK else 30
            due_date = inv_date + timedelta(days=days)
            self.query_one("#lbl-due", Static).update(f"Due: {due_date}")
        except (ValueError, TypeError):
            self.query_one("#lbl-due", Static).update("Due: (enter a valid INV date)")

    def _refresh_dn_table(self) -> None:
        tbl = self.query_one("#dn-tbl", DataTable)
        tbl.clear()
        if not self._customer_id:
            self.query_one("#dn-hint", Static).update("Pick a customer to see available DN.")
            return
        sym = get_currency_symbol()
        rows = dndata.fetch_issued_for_customer(self._customer_id)
        for row in rows:
            sel = "[X]" if row[0] in self._selected_dn_ids else "[ ]"
            tbl.add_row(
                sel, str(row[0]), row[1], row[2], f"{sym}{float(row[3]):.2f}",
                key=str(row[0]),
            )
        if not rows:
            self.query_one("#dn-hint", Static).update("No issued DN documents for this customer.")
        else:
            count = len(self._selected_dn_ids)
            self.query_one("#dn-hint", Static).update(
                f"{len(rows)} available · {count} selected (press Space to toggle)"
            )

    @on(Input.Changed, "#f-invdate")
    def on_invdate_changed(self, event: Input.Changed) -> None:
        self._update_due_label()

    @on(Select.Changed, "#f-terms")
    def on_terms_changed(self, event: Select.Changed) -> None:
        self._update_due_label()

    @on(Button.Pressed, "#btn-pick-cust")
    def on_pick_customer(self) -> None:
        rows = cdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._customer_id = pk
                self._selected_dn_ids.clear()
                cust = cdata.get_by_pk(pk)
                if cust:
                    self._customer_name = cust["CompanyName"]
                    self.query_one("#lbl-customer", Label).update(cust["CompanyName"])
                self._refresh_dn_table()
        self.app.push_screen(
            PickerModal("Select Customer",
                        [("ID", 6), ("Company", 26), ("Contact", 18), ("City", 12)], rows),
            callback=after,
        )

    @on(DataTable.RowSelected, "#dn-tbl")
    def on_dn_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key:
            dn_id = int(event.row_key.value)
            if dn_id in self._selected_dn_ids:
                self._selected_dn_ids.discard(dn_id)
            else:
                self._selected_dn_ids.add(dn_id)
            self._refresh_dn_table()

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        from datetime import datetime
        if not self._customer_id:
            self.notify("Customer is required.", severity="error")
            return
        if not self._selected_dn_ids:
            self.notify("Select at least one DN document.", severity="error")
            return
        inv_date = self.query_one("#f-invdate", Input).value.strip()
        try:
            datetime.strptime(inv_date, "%Y-%m-%d")
        except ValueError:
            self.notify("INV Date must be YYYY-MM-DD.", severity="error")
            return
        terms = self.query_one("#f-terms", Select).value
        payment_term_days = int(terms) if terms != Select.BLANK else 30
        payment = self.query_one("#f-payment", Select).value
        if payment == "(none)":
            payment = ""
        notes = self.query_one("#f-notes", Input).value.strip()
        try:
            inv_id = invdata.create(
                self._customer_id, list(self._selected_dn_ids),
                inv_date, payment_term_days, payment, notes,
            )
            self.notify(f"Invoice created (INV #{inv_id}).", severity="information")
            self.dismiss(inv_id)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class RecordPaymentModal(ModalScreen):
    """Modal to record a payment against an INV invoice."""

    def __init__(self, inv_id: int, outstanding: float,
                 preferred_method: str = "bank") -> None:
        super().__init__()
        self.inv_id = inv_id
        self.outstanding = outstanding
        self.preferred_method = preferred_method

    def compose(self) -> ComposeResult:
        sym = get_currency_symbol()
        with Vertical(classes="modal-dialog"):
            yield Label(f"Record Payment — INV #{self.inv_id}", classes="modal-title")
            yield Label(f"Outstanding: {sym}{self.outstanding:.2f}")
            yield Label("Amount:")
            yield Input(id="f-amount", value=f"{self.outstanding:.2f}")
            yield Label("Method:")
            yield Select(
                [("bank", "bank"), ("cash", "cash")],
                id="f-method",
                value=self.preferred_method if self.preferred_method in ("bank", "cash") else "bank",
            )
            yield Label("Description:")
            yield Input(id="f-desc", placeholder="Optional description")
            with Horizontal(classes="modal-buttons"):
                yield Button("Record", id="btn-record", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    @on(Button.Pressed, "#btn-record")
    def on_record(self) -> None:
        try:
            amount = float(self.query_one("#f-amount", Input).value.strip())
        except ValueError:
            self.notify("Amount must be a number.", severity="error")
            return
        if amount <= 0:
            self.notify("Amount must be positive.", severity="error")
            return
        method = self.query_one("#f-method", Select).value
        if method == Select.BLANK:
            method = "bank"
        desc = self.query_one("#f-desc", Input).value.strip()
        try:
            invdata.record_payment(self.inv_id, amount, method, desc)
            self.notify("Payment recorded.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class INVDetailModal(ModalScreen):
    """Full INV detail with linked DN, line items, and payment tracking."""

    def __init__(self, inv_id: int) -> None:
        super().__init__()
        self.inv_id = inv_id
        self._changed = False

    def compose(self) -> ComposeResult:
        with Vertical(classes="order-detail-dialog"):
            yield Label("", id="inv-title", classes="modal-title")
            yield Static("", id="inv-header")
            yield Label("Linked DN Documents:", classes="section-label")
            yield DataTable(id="dn-tbl", cursor_type="row", zebra_stripes=True)
            yield Label("Line Items (from all DN):", classes="section-label")
            yield DataTable(id="lines-tbl", cursor_type="row", zebra_stripes=True)
            yield Static("", id="inv-payment")
            yield Label("Linked CN (Credit Notes):", classes="section-label")
            yield DataTable(id="cn-tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="modal-buttons"):
                yield Button("Record Payment", id="btn-record-payment", variant="primary")
                yield Button("Issue CN",       id="btn-issue-cn",       variant="warning")
                yield Button("Cancel INV",     id="btn-cancel-doc",     variant="warning")
                yield Button("Delete",         id="btn-delete",         variant="error")
                yield Button("PDF",            id="btn-pdf",            variant="default")
                yield Button("Close",          id="btn-close")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        dn_tbl = self.query_one("#dn-tbl", DataTable)
        for label, width in [("DN_ID", 6), ("Number", 20), ("Date", 12), ("Total", 12)]:
            dn_tbl.add_column(label, width=width)
        lines_tbl = self.query_one("#lines-tbl", DataTable)
        for label, width in [
            ("ProdID", 6), ("Product Name", 36), ("Qty", 6), ("Price", 12), ("Line Total", 12),
        ]:
            lines_tbl.add_column(label, width=width)
        cn_tbl = self.query_one("#cn-tbl", DataTable)
        for label, width in [
            ("CN_ID", 6), ("Number", 20), ("Date", 12), ("Type", 16), ("Correction", 12),
        ]:
            cn_tbl.add_column(label, width=width)
        self._load()

    def _load(self) -> None:
        sym = get_currency_symbol()
        hdr = invdata.get_by_pk(self.inv_id)
        if not hdr:
            self.dismiss(self._changed)
            return
        self.query_one("#inv-title", Label).update(f"INV #{self.inv_id} — {hdr.get('INV_Number', '')}")
        info = [
            f"[b]Number:[/b]   {hdr.get('INV_Number', '')}",
            f"[b]Customer:[/b] {hdr.get('CustomerID', '')} — {hdr.get('CompanyName') or ''}",
            f"[b]Date:[/b]     {hdr.get('INV_Date', '')}   "
            f"[b]Due:[/b] {hdr.get('DueDate') or '—'}   "
            f"[b]Terms:[/b] {hdr.get('PaymentTermDays') or 0} days",
            f"[b]Pref. Payment:[/b]  {hdr.get('PaymentMethod') or '—'}   "
            f"[b]Status:[/b] {hdr.get('Status', '')}",
        ]
        if hdr.get("Notes"):
            info.append(f"[b]Notes:[/b] {hdr['Notes']}")
        self.query_one("#inv-header", Static).update("\n".join(info))

        dn_tbl = self.query_one("#dn-tbl", DataTable)
        dn_tbl.clear()
        for dn in invdata.fetch_linked_dn(self.inv_id):
            dn_tbl.add_row(
                str(dn["DN_ID"]), dn["DN_Number"], dn["DN_Date"],
                f"{sym}{dn['Total']:.2f}",
            )

        lines_tbl = self.query_one("#lines-tbl", DataTable)
        lines_tbl.clear()
        for it in invdata.fetch_line_items(self.inv_id):
            lt = it["LineTotal"]
            lines_tbl.add_row(
                str(it["ProductID"]), it["ProductName"], str(it["Quantity"]),
                f"{sym}{it['UnitPrice']:.2f}", f"{sym}{lt:.2f}",
            )

        total_net   = hdr.get("TotalNet") or 0.0
        paid        = hdr.get("PaidAmount") or 0.0
        outstanding = hdr.get("Outstanding") or (total_net - paid)
        out_style   = "[bold red]" if outstanding > 0 else "[bold]"
        self.query_one("#inv-payment", Static).update(
            f"[b]Total Net:[/b]   {sym}{total_net:.2f}\n"
            f"[b]Paid:[/b]        {sym}{paid:.2f}\n"
            f"{out_style}Outstanding: {sym}{outstanding:.2f}[/]"
        )

        # Load linked CN (credit notes)
        cn_tbl = self.query_one("#cn-tbl", DataTable)
        cn_tbl.clear()
        try:
            import data.cn as cndata
            cn_docs = cndata.fetch_for_inv(self.inv_id)
            for cn in cn_docs:
                cn_tbl.add_row(
                    str(cn["CN_ID"]), cn["CN_Number"], cn["CN_Date"],
                    cn["CN_Type"], f"{sym}{cn['TotalCorrection']:.2f}",
                )
        except Exception:
            pass

        # Show cancellation info if cancelled
        if hdr.get("CancelledAt"):
            info.append(
                f"[b]CANCELLED[/b] on {hdr['CancelledAt'][:19]} by user #{hdr.get('CancelledBy', '?')}: "
                f"{hdr.get('CancelReason', '')}"
            )
            self.query_one("#inv-header", Static).update("\n".join(info))

        # Adjust buttons based on status and role
        status = hdr.get("Status", "issued")
        is_cancelled = status == "cancelled"
        is_admin = has_permission(getattr(self.app, "_current_user", None), "admin")
        is_manager = has_permission(getattr(self.app, "_current_user", None), "manager")
        paid_amount = hdr.get("PaidAmount") or 0.0
        try:
            self.query_one("#btn-record-payment", Button).disabled = (
                status in ("paid", "cancelled")
            )
            self.query_one("#btn-delete", Button).disabled = (not is_manager or is_cancelled)
            cancel_btn = self.query_one("#btn-cancel-doc", Button)
            cancel_btn.disabled = (
                status != "issued" or paid_amount > 0 or not is_admin
            )
            cancel_btn.display = is_admin
            cn_btn = self.query_one("#btn-issue-cn", Button)
            cn_btn.disabled = (is_cancelled or not is_admin)
            cn_btn.display = is_admin
        except Exception:
            pass

    @on(Button.Pressed, "#btn-record-payment")
    def on_record_payment(self) -> None:
        hdr = invdata.get_by_pk(self.inv_id)
        if not hdr:
            return
        outstanding = hdr.get("Outstanding") or 0.0
        preferred   = hdr.get("PaymentMethod") or "bank"

        def after(recorded):
            if recorded:
                self._changed = True
                self._load()

        self.app.push_screen(
            RecordPaymentModal(self.inv_id, outstanding, preferred),
            callback=after,
        )

    @on(Button.Pressed, "#btn-cancel-doc")
    def on_cancel_doc(self) -> None:
        def after(reason):
            if reason:
                try:
                    user_id = getattr(self.app, "_current_user", {}).get("user_id", 0)
                    invdata.cancel(self.inv_id, reason, user_id)
                    self._changed = True
                    self._load()
                    self.notify("INV cancelled — linked DN reverted to 'issued'.", severity="information")
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
        self.app.push_screen(
            CancellationReasonModal(
                f"Cancel INV #{self.inv_id}?",
                "Linked DN will revert to 'issued'. Stock is NOT reversed.",
            ),
            callback=after,
        )

    @on(Button.Pressed, "#btn-issue-cn")
    def on_issue_cn(self) -> None:
        from screens.cn import CNNewModal
        def after(cn_id):
            if cn_id:
                self._changed = True
                self._load()
        self.app.push_screen(CNNewModal(self.inv_id), callback=after)

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        def after(confirmed):
            if confirmed:
                try:
                    invdata.delete(self.inv_id)
                    self.dismiss(True)
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"INV #{self.inv_id}"), callback=after)

    @on(Button.Pressed, "#btn-pdf")
    def on_pdf(self) -> None:
        try:
            import pdf_export
            path = pdf_export.export_inv(self.inv_id)
            self.notify(f"PDF saved → {path}", severity="information")
        except Exception as e:
            self.notify(f"PDF error: {e}", severity="error")

    @on(Button.Pressed, "#btn-close")
    def on_close(self) -> None:
        self.dismiss(self._changed)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(self._changed)


class INVPanel(Widget):
    BINDINGS = [
        ("n", "new_record",   "New INV"),
        ("f", "focus_search", "Search"),
    ]

    _selected_pk = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Input(placeholder="Search invoices...", id="search-box")
            yield DataTable(id="tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("+ New Invoice", id="btn-new",    variant="success")
                yield Button("Open",          id="btn-open")
                yield Button("Delete",        id="btn-delete", variant="error")
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        for label, width in [
            ("ID", 6), ("Number", 16), ("Date", 12), ("Customer", 22),
            ("Status", 8), ("Payment", 8), ("Total", 12),
        ]:
            tbl.add_column(label, width=width)
        self.refresh_data()

    def refresh_data(self, term: str = "") -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        rows = invdata.search(term) if term else invdata.fetch_all()
        sym = get_currency_symbol()
        for row in rows:
            display = list(row)
            if display[6] is not None:
                display[6] = f"{sym}{float(display[6]):.2f}"
            tbl.add_row(*[str(c) if c is not None else "" for c in display],
                        key=str(row[0]))
        try:
            self.query_one("#count-label", Label).update(f"{len(rows)} records")
        except Exception:
            pass

    @on(Input.Changed, "#search-box")
    def on_search(self, event: Input.Changed) -> None:
        self.refresh_data(event.value)

    @on(DataTable.RowHighlighted, "#tbl")
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._selected_pk = event.row_key.value

    @on(DataTable.RowSelected, "#tbl")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key:
            self._open_detail(int(event.row_key.value))

    def _open_detail(self, inv_id: int) -> None:
        def after(changed):
            if changed:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(INVDetailModal(inv_id), callback=after)

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-open")
    def on_btn_open(self) -> None:
        if self._selected_pk:
            self._open_detail(int(self._selected_pk))
        else:
            self.notify("Select an invoice first.", severity="warning")

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        if not self._selected_pk:
            self.notify("Select an invoice first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    invdata.delete(int(self._selected_pk))
                    self._selected_pk = None
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify("Invoice deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"INV #{self._selected_pk}"), callback=after)

    def action_new_record(self) -> None:
        def after_form(inv_id):
            if inv_id:
                def after_detail(changed):
                    self.refresh_data(self.query_one("#search-box", Input).value)
                self.app.push_screen(INVDetailModal(inv_id), callback=after_detail)
        self.app.push_screen(INVNewModal(), callback=after_form)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()
