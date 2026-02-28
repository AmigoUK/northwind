from __future__ import annotations
"""screens/gr.py — GR (Goods Receipt) panel, detail, and form modals."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static
from textual import on

import data.gr as grdata
import data.suppliers as sdata
import data.products as pdata
from data.settings import get_currency_symbol
from data.users import has_permission
from screens.modals import ConfirmActionModal, ConfirmDeleteModal, CancellationReasonModal, PickerModal


class GRItemFormModal(ModalScreen):
    """Add a line item to a GR document."""

    def __init__(self, gr_id: int) -> None:
        super().__init__()
        self.gr_id = gr_id
        self._product_id = None
        self._product_name = ""

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(f"Add Item to GR #{self.gr_id}", classes="modal-title")
            yield Label("Product:")
            with Horizontal():
                yield Label("(none)", id="lbl-product")
                yield Button("Pick Product", id="btn-pick-prod")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Unit Cost:")
                    yield Input(id="f-cost", placeholder="0.00")
                with Vertical(classes="form-field"):
                    yield Label("Quantity:")
                    yield Input(id="f-qty", value="1", placeholder="1")
            with Horizontal(classes="modal-buttons"):
                yield Button("Add", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    @on(Button.Pressed, "#btn-pick-prod")
    def on_pick_product(self) -> None:
        rows = pdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._product_id = int(pk)
                prod = pdata.get_by_pk(int(pk))
                if prod:
                    self._product_name = prod["ProductName"]
                    self.query_one("#lbl-product", Label).update(prod["ProductName"])
                    self.query_one("#f-cost", Input).value = str(prod.get("UnitPrice", 0.0))
        self.app.push_screen(
            PickerModal(
                "Select Product",
                [("ID", 4), ("Product Name", 28), ("Category", 16), ("Price", 8), ("Stock", 6)],
                rows,
            ),
            callback=after,
        )

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        if not self._product_id:
            self.notify("Select a product first.", severity="error")
            return
        try:
            cost = float(self.query_one("#f-cost", Input).value.strip() or "0")
            qty  = int(self.query_one("#f-qty",  Input).value.strip() or "1")
        except ValueError:
            self.notify("Cost and Quantity must be numbers.", severity="error")
            return
        if qty < 1:
            self.notify("Quantity must be at least 1.", severity="error")
            return
        try:
            grdata.add_item(self.gr_id, self._product_id, qty, cost)
            self.notify(f"'{self._product_name}' added.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class GRFormModal(ModalScreen):
    """Create a new GR document (draft)."""

    def __init__(self, supplier_id: int | None = None) -> None:
        super().__init__()
        self._supplier_id = supplier_id
        self._supplier_name = ""

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("New GR — Goods Receipt", classes="modal-title")
            yield Label("Supplier *:")
            with Horizontal():
                yield Label("(none)", id="lbl-supplier")
                yield Button("Pick Supplier", id="btn-pick-sup")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("GR Date (YYYY-MM-DD) *:")
                    yield Input(id="f-date", placeholder="2026-01-01")
                with Vertical(classes="form-field"):
                    yield Label("Supplier Doc Ref:")
                    yield Input(id="f-supref", placeholder="Supplier invoice/ref")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Payment Method:")
                    yield Select(
                        [("cash", "cash"), ("bank", "bank"), ("(none)", "(none)")],
                        id="f-payment", value="bank",
                    )
                with Vertical(classes="form-field"):
                    yield Label("Notes:")
                    yield Input(id="f-notes", placeholder="Optional notes")
            with Horizontal(classes="modal-buttons"):
                yield Button("Create Draft", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        from datetime import date
        self.query_one("#f-date", Input).value = str(date.today())
        if self._supplier_id:
            sup = sdata.get_by_pk(self._supplier_id)
            if sup:
                self._supplier_name = sup["CompanyName"]
                self.query_one("#lbl-supplier", Label).update(sup["CompanyName"])

    @on(Button.Pressed, "#btn-pick-sup")
    def on_pick_supplier(self) -> None:
        rows = sdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._supplier_id = int(pk)
                sup = sdata.get_by_pk(int(pk))
                if sup:
                    self._supplier_name = sup["CompanyName"]
                    self.query_one("#lbl-supplier", Label).update(sup["CompanyName"])
        self.app.push_screen(
            PickerModal("Select Supplier",
                        [("ID", 4), ("Company", 26), ("City", 14), ("Country", 12)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        from datetime import datetime
        if not self._supplier_id:
            self.notify("Supplier is required.", severity="error")
            return
        gr_date = self.query_one("#f-date", Input).value.strip()
        if not gr_date:
            self.notify("GR Date is required.", severity="error")
            return
        try:
            datetime.strptime(gr_date, "%Y-%m-%d")
        except ValueError:
            self.notify("Date must be YYYY-MM-DD.", severity="error")
            return
        sup_ref = self.query_one("#f-supref", Input).value.strip()
        payment = self.query_one("#f-payment", Select).value
        if payment == "(none)":
            payment = ""
        notes = self.query_one("#f-notes", Input).value.strip()
        try:
            gr_id = grdata.create_draft(self._supplier_id, gr_date, sup_ref, payment, notes)
            self.notify(f"GR draft created (ID #{gr_id}).", severity="information")
            self.dismiss(gr_id)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class GRDetailModal(ModalScreen):
    """Full GR detail with line items."""

    def __init__(self, gr_id: int) -> None:
        super().__init__()
        self.gr_id = gr_id
        self._changed = False
        self._selected_product_id = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="order-detail-dialog"):
            yield Label("", id="gr-title", classes="modal-title")
            yield Static("", id="gr-header")
            yield Label("Line Items:", classes="section-label")
            yield DataTable(id="items-tbl", cursor_type="row", zebra_stripes=True)
            yield Static("", id="gr-total")
            with Horizontal(classes="modal-buttons"):
                yield Button("Receive",    id="btn-receive",    variant="primary")
                yield Button("+ Item",     id="btn-add",        variant="success")
                yield Button("- Item",     id="btn-remove",     variant="warning")
                yield Button("Cancel GR",  id="btn-cancel-doc", variant="warning")
                yield Button("Delete",     id="btn-delete",     variant="error")
                yield Button("PDF",        id="btn-pdf",        variant="default")
                yield Button("Close",      id="btn-close")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        tbl = self.query_one("#items-tbl", DataTable)
        for label, width in [
            ("ProdID", 6), ("Product Name", 36), ("Qty", 6),
            ("Unit Cost", 12), ("Line Total", 12),
        ]:
            tbl.add_column(label, width=width)
        self._load()

    def _load(self) -> None:
        sym = get_currency_symbol()
        hdr = grdata.get_by_pk(self.gr_id)
        if not hdr:
            self.dismiss(self._changed)
            return
        self.query_one("#gr-title", Label).update(f"GR #{self.gr_id} — {hdr.get('GR_Number', '')}")
        info = [
            f"[b]Number:[/b]   {hdr.get('GR_Number', '')}",
            f"[b]Supplier:[/b] #{hdr.get('SupplierID', '')} — {hdr.get('CompanyName') or ''}",
            f"[b]Date:[/b]     {hdr.get('GR_Date', '')}   [b]Status:[/b] {hdr.get('Status', '')}",
            f"[b]Payment:[/b]  {hdr.get('PaymentMethod') or '—'}",
        ]
        if hdr.get("SupplierDocRef"):
            info.append(f"[b]Supplier Ref:[/b] {hdr['SupplierDocRef']}")
        if hdr.get("Notes"):
            info.append(f"[b]Notes:[/b] {hdr['Notes']}")
        self.query_one("#gr-header", Static).update("\n".join(info))

        tbl = self.query_one("#items-tbl", DataTable)
        tbl.clear()
        items = grdata.fetch_items(self.gr_id)
        total = 0.0
        for it in items:
            lt = it["LineTotal"]
            total += lt
            tbl.add_row(
                str(it["ProductID"]), it["ProductName"], str(it["Quantity"]),
                f"{sym}{it['UnitCost']:.2f}", f"{sym}{lt:.2f}",
                key=str(it["ProductID"]),
            )
        self.query_one("#gr-total", Static).update(f"[b]Total Cost:[/b] {sym}{total:.2f}")

        # Show cancellation info if cancelled
        if hdr.get("CancelledAt"):
            info.append(
                f"[b]CANCELLED[/b] on {hdr['CancelledAt'][:19]} by user #{hdr.get('CancelledBy', '?')}: "
                f"{hdr.get('CancelReason', '')}"
            )
            self.query_one("#gr-header", Static).update("\n".join(info))

        status = hdr.get("Status", "draft")
        is_cancelled = status == "cancelled"
        is_admin = has_permission(getattr(self.app, "_current_user", None), "admin")
        is_manager = has_permission(getattr(self.app, "_current_user", None), "manager")
        try:
            self.query_one("#btn-receive", Button).disabled = (status != "draft" or is_cancelled)
            self.query_one("#btn-add",     Button).disabled = (status != "draft" or is_cancelled)
            self.query_one("#btn-remove",  Button).disabled = (status != "draft" or is_cancelled)
            self.query_one("#btn-delete",  Button).disabled = (status != "draft" or not is_manager)
            cancel_btn = self.query_one("#btn-cancel-doc", Button)
            cancel_btn.disabled = (status != "received" or not is_admin)
            cancel_btn.display = is_admin
        except Exception:
            pass

    @on(DataTable.RowHighlighted, "#items-tbl")
    def on_item_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._selected_product_id = event.row_key.value

    @on(Button.Pressed, "#btn-receive")
    def on_receive(self) -> None:
        def after(confirmed):
            if confirmed:
                try:
                    grdata.receive(self.gr_id)
                    self._changed = True
                    self._load()
                    self.notify("GR received — stock updated.", severity="information")
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
        self.app.push_screen(
            ConfirmActionModal(
                f"Receive GR #{self.gr_id}?",
                "Stock will be increased for each line item.",
                confirm_label="Receive",
            ),
            callback=after,
        )

    @on(Button.Pressed, "#btn-add")
    def on_add_item(self) -> None:
        def after(saved):
            if saved:
                self._changed = True
                self._load()
        self.app.push_screen(GRItemFormModal(self.gr_id), callback=after)

    @on(Button.Pressed, "#btn-remove")
    def on_remove_item(self) -> None:
        if not self._selected_product_id:
            self.notify("Select a line item first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    grdata.remove_item(self.gr_id, int(self._selected_product_id))
                    self._selected_product_id = None
                    self._changed = True
                    self._load()
                    self.notify("Item removed.", severity="information")
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal("this line item"), callback=after)

    @on(Button.Pressed, "#btn-cancel-doc")
    def on_cancel_doc(self) -> None:
        def after(reason):
            if reason:
                try:
                    user_id = getattr(self.app, "_current_user", {}).get("user_id", 0)
                    grdata.cancel(self.gr_id, reason, user_id)
                    self._changed = True
                    self._load()
                    self.notify("GR cancelled — stock reversed.", severity="information")
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
        self.app.push_screen(
            CancellationReasonModal(
                f"Cancel GR #{self.gr_id}?",
                "Stock will be reversed. Linked payment docs will NOT be deleted.",
            ),
            callback=after,
        )

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        def after(confirmed):
            if confirmed:
                try:
                    grdata.delete(self.gr_id)
                    self.dismiss(True)
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"GR #{self.gr_id}"), callback=after)

    @on(Button.Pressed, "#btn-pdf")
    def on_pdf(self) -> None:
        try:
            import pdf_export
            path = pdf_export.export_gr(self.gr_id)
            self.notify(f"PDF saved → {path}", severity="information")
        except Exception as e:
            self.notify(f"PDF error: {e}", severity="error")

    @on(Button.Pressed, "#btn-close")
    def on_close(self) -> None:
        self.dismiss(self._changed)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(self._changed)


class GRPanel(Widget):
    BINDINGS = [
        ("n", "new_record",   "New GR"),
        ("f", "focus_search", "Search"),
    ]

    _selected_pk = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Input(placeholder="Search GR documents...", id="search-box")
            yield DataTable(id="tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("+ New",  id="btn-new",    variant="success")
                yield Button("Open",   id="btn-open")
                yield Button("Delete", id="btn-delete", variant="error")
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        for label, width in [
            ("ID", 6), ("Number", 16), ("Date", 12), ("Supplier", 24),
            ("Status", 10), ("Total Cost", 12),
        ]:
            tbl.add_column(label, width=width)
        self.refresh_data()

    def refresh_data(self, term: str = "") -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        rows = grdata.search(term) if term else grdata.fetch_all()
        sym = get_currency_symbol()
        for row in rows:
            display = list(row)
            if display[5] is not None:
                display[5] = f"{sym}{float(display[5]):.2f}"
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

    def _open_detail(self, gr_id: int) -> None:
        def after(changed):
            if changed:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(GRDetailModal(gr_id), callback=after)

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-open")
    def on_btn_open(self) -> None:
        if self._selected_pk:
            self._open_detail(int(self._selected_pk))
        else:
            self.notify("Select a GR document first.", severity="warning")

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        if not self._selected_pk:
            self.notify("Select a GR document first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    grdata.delete(int(self._selected_pk))
                    self._selected_pk = None
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify("GR deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"GR #{self._selected_pk}"), callback=after)

    def action_new_record(self) -> None:
        def after_form(gr_id):
            if gr_id:
                def after_detail(changed):
                    self.refresh_data(self.query_one("#search-box", Input).value)
                self.app.push_screen(GRDetailModal(gr_id), callback=after_detail)
        self.app.push_screen(GRFormModal(), callback=after_form)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()
