from __future__ import annotations
"""screens/pz.py — PZ (Przyjęcie Zewnętrzne) panel, detail, and form modals."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static
from textual import on

import data.pz as pzdata
import data.suppliers as sdata
import data.products as pdata
from data.settings import get_currency_symbol
from screens.modals import ConfirmActionModal, ConfirmDeleteModal, PickerModal


class PZItemFormModal(ModalScreen):
    """Add a line item to a PZ document."""

    def __init__(self, pz_id: int) -> None:
        super().__init__()
        self.pz_id = pz_id
        self._product_id = None
        self._product_name = ""

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(f"Add Item to PZ #{self.pz_id}", classes="modal-title")
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
            pzdata.add_item(self.pz_id, self._product_id, qty, cost)
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


class PZFormModal(ModalScreen):
    """Create a new PZ document (draft)."""

    def __init__(self, supplier_id: int | None = None) -> None:
        super().__init__()
        self._supplier_id = supplier_id
        self._supplier_name = ""

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("New PZ — Przyjęcie Zewnętrzne", classes="modal-title")
            yield Label("Supplier *:")
            with Horizontal():
                yield Label("(none)", id="lbl-supplier")
                yield Button("Pick Supplier", id="btn-pick-sup")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("PZ Date (YYYY-MM-DD) *:")
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
        pz_date = self.query_one("#f-date", Input).value.strip()
        if not pz_date:
            self.notify("PZ Date is required.", severity="error")
            return
        try:
            datetime.strptime(pz_date, "%Y-%m-%d")
        except ValueError:
            self.notify("Date must be YYYY-MM-DD.", severity="error")
            return
        sup_ref = self.query_one("#f-supref", Input).value.strip()
        payment = self.query_one("#f-payment", Select).value
        if payment == "(none)":
            payment = ""
        notes = self.query_one("#f-notes", Input).value.strip()
        try:
            pz_id = pzdata.create_draft(self._supplier_id, pz_date, sup_ref, payment, notes)
            self.notify(f"PZ draft created (ID #{pz_id}).", severity="information")
            self.dismiss(pz_id)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class PZDetailModal(ModalScreen):
    """Full PZ detail with line items."""

    def __init__(self, pz_id: int) -> None:
        super().__init__()
        self.pz_id = pz_id
        self._changed = False
        self._selected_product_id = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="order-detail-dialog"):
            yield Label("", id="pz-title", classes="modal-title")
            yield Static("", id="pz-header")
            yield Label("Line Items:", classes="section-label")
            yield DataTable(id="items-tbl", cursor_type="row", zebra_stripes=True)
            yield Static("", id="pz-total")
            with Horizontal(classes="modal-buttons"):
                yield Button("Receive",  id="btn-receive", variant="primary")
                yield Button("+ Item",   id="btn-add",     variant="success")
                yield Button("- Item",   id="btn-remove",  variant="warning")
                yield Button("Delete",   id="btn-delete",  variant="error")
                yield Button("Close",    id="btn-close")
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
        hdr = pzdata.get_by_pk(self.pz_id)
        if not hdr:
            self.dismiss(self._changed)
            return
        self.query_one("#pz-title", Label).update(f"PZ #{self.pz_id} — {hdr.get('PZ_Number', '')}")
        info = [
            f"[b]Number:[/b]   {hdr.get('PZ_Number', '')}",
            f"[b]Supplier:[/b] #{hdr.get('SupplierID', '')} — {hdr.get('CompanyName') or ''}",
            f"[b]Date:[/b]     {hdr.get('PZ_Date', '')}   [b]Status:[/b] {hdr.get('Status', '')}",
            f"[b]Payment:[/b]  {hdr.get('PaymentMethod') or '—'}",
        ]
        if hdr.get("SupplierDocRef"):
            info.append(f"[b]Supplier Ref:[/b] {hdr['SupplierDocRef']}")
        if hdr.get("Notes"):
            info.append(f"[b]Notes:[/b] {hdr['Notes']}")
        self.query_one("#pz-header", Static).update("\n".join(info))

        tbl = self.query_one("#items-tbl", DataTable)
        tbl.clear()
        items = pzdata.fetch_items(self.pz_id)
        total = 0.0
        for it in items:
            lt = it["LineTotal"]
            total += lt
            tbl.add_row(
                str(it["ProductID"]), it["ProductName"], str(it["Quantity"]),
                f"{sym}{it['UnitCost']:.2f}", f"{sym}{lt:.2f}",
                key=str(it["ProductID"]),
            )
        self.query_one("#pz-total", Static).update(f"[b]Total Cost:[/b] {sym}{total:.2f}")

        status = hdr.get("Status", "draft")
        try:
            self.query_one("#btn-receive", Button).disabled = (status != "draft")
            self.query_one("#btn-add",     Button).disabled = (status != "draft")
            self.query_one("#btn-remove",  Button).disabled = (status != "draft")
            self.query_one("#btn-delete",  Button).disabled = (status == "received")
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
                    pzdata.receive(self.pz_id)
                    self._changed = True
                    self._load()
                    self.notify("PZ received — stock updated.", severity="information")
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
        self.app.push_screen(
            ConfirmActionModal(
                f"Receive PZ #{self.pz_id}?",
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
        self.app.push_screen(PZItemFormModal(self.pz_id), callback=after)

    @on(Button.Pressed, "#btn-remove")
    def on_remove_item(self) -> None:
        if not self._selected_product_id:
            self.notify("Select a line item first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    pzdata.remove_item(self.pz_id, int(self._selected_product_id))
                    self._selected_product_id = None
                    self._changed = True
                    self._load()
                    self.notify("Item removed.", severity="information")
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal("this line item"), callback=after)

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        def after(confirmed):
            if confirmed:
                try:
                    pzdata.delete(self.pz_id)
                    self.dismiss(True)
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"PZ #{self.pz_id}"), callback=after)

    @on(Button.Pressed, "#btn-close")
    def on_close(self) -> None:
        self.dismiss(self._changed)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(self._changed)


class PZPanel(Widget):
    BINDINGS = [
        ("n", "new_record",   "New PZ"),
        ("f", "focus_search", "Search"),
    ]

    _selected_pk = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Input(placeholder="Search PZ documents...", id="search-box")
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
        rows = pzdata.search(term) if term else pzdata.fetch_all()
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

    def _open_detail(self, pz_id: int) -> None:
        def after(changed):
            if changed:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(PZDetailModal(pz_id), callback=after)

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-open")
    def on_btn_open(self) -> None:
        if self._selected_pk:
            self._open_detail(int(self._selected_pk))
        else:
            self.notify("Select a PZ document first.", severity="warning")

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        if not self._selected_pk:
            self.notify("Select a PZ document first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    pzdata.delete(int(self._selected_pk))
                    self._selected_pk = None
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify("PZ deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"PZ #{self._selected_pk}"), callback=after)

    def action_new_record(self) -> None:
        def after_form(pz_id):
            if pz_id:
                def after_detail(changed):
                    self.refresh_data(self.query_one("#search-box", Input).value)
                self.app.push_screen(PZDetailModal(pz_id), callback=after_detail)
        self.app.push_screen(PZFormModal(), callback=after_form)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()
