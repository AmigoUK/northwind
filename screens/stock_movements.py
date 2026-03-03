from __future__ import annotations
"""screens/stock_movements.py — SI/SO (internal stock movements) panel."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static, TabbedContent, TabPane
from textual import on

import data.si_so as siso
import data.products as pdata
from data.settings import get_backorder_allowed
from screens.modals import ConfirmDeleteModal, PickerModal


class MovementItemRow:
    """Temporary storage for a pending line item during form creation."""
    __slots__ = ("product_id", "product_name", "quantity")

    def __init__(self, product_id: int, product_name: str, quantity: int) -> None:
        self.product_id = product_id
        self.product_name = product_name
        self.quantity = quantity


class MovementFormModal(ModalScreen):
    """Create a new SI or SO movement document."""

    def __init__(self, doc_type: str) -> None:
        super().__init__()
        self.doc_type = doc_type  # "SI" or "SO"
        self._items: list[MovementItemRow] = []
        self._selected_idx: int | None = None

    def compose(self) -> ComposeResult:
        title = "SI — Stock Issue" if self.doc_type == "SI" else "SO — Stock Out"
        with Vertical(classes="order-detail-dialog"):
            yield Label(f"New {title}", classes="modal-title")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Date (YYYY-MM-DD) *:")
                    yield Input(id="f-date", placeholder="2026-01-01")
                with Vertical(classes="form-field"):
                    yield Label("Reason:")
                    yield Input(id="f-reason", placeholder="Reason / description")
            yield Label("Items:", classes="section-label")
            yield DataTable(id="items-tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal():
                yield Button("+ Add Item", id="btn-add-item", variant="success")
                yield Button("- Remove",   id="btn-rem-item", variant="warning")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        from datetime import date
        self.query_one("#f-date", Input).value = str(date.today())
        tbl = self.query_one("#items-tbl", DataTable)
        for label, width in [("Product Name", 32), ("Quantity", 10)]:
            tbl.add_column(label, width=width)

    def _refresh_items_table(self) -> None:
        tbl = self.query_one("#items-tbl", DataTable)
        tbl.clear()
        for i, item in enumerate(self._items):
            tbl.add_row(item.product_name, str(item.quantity), key=str(i))

    @on(DataTable.RowHighlighted, "#items-tbl")
    def on_item_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            try:
                self._selected_idx = int(event.row_key.value)
            except (ValueError, TypeError):
                self._selected_idx = None

    @on(Button.Pressed, "#btn-add-item")
    def on_add_item(self) -> None:
        rows = pdata.fetch_for_picker()
        def after_product(pk):
            if not pk:
                return
            prod = pdata.get_by_pk(int(pk))
            if not prod:
                return

            class QtyModal(ModalScreen):
                def compose(inner_self) -> ComposeResult:
                    with Vertical(classes="confirm-dialog"):
                        yield Label(f"Quantity for {prod['ProductName']}:", classes="modal-title")
                        yield Input(id="f-qty", value="1", placeholder="1")
                        with Horizontal(classes="modal-buttons"):
                            yield Button("Add", id="btn-ok", variant="primary")
                            yield Button("Cancel", id="btn-cancel")

                @on(Button.Pressed, "#btn-ok")
                def on_ok(inner_self) -> None:
                    try:
                        qty = int(inner_self.query_one("#f-qty", Input).value.strip() or "1")
                    except ValueError:
                        inner_self.notify("Quantity must be a number.", severity="error")
                        return
                    if qty < 1:
                        inner_self.notify("Quantity must be at least 1.", severity="error")
                        return
                    inner_self.dismiss(qty)

                @on(Button.Pressed, "#btn-cancel")
                def on_cancel(inner_self) -> None:
                    inner_self.dismiss(None)

                def on_key(inner_self, event) -> None:
                    if event.key == "escape":
                        inner_self.dismiss(None)

            def after_qty(qty):
                if qty:
                    if self.doc_type == "SO":
                        available = pdata.get_stock(int(pk))
                        if qty > available:
                            if get_backorder_allowed():
                                self.notify(
                                    f"Stock: {available} available. Backorder active — saving {qty}.",
                                    severity="warning",
                                )
                            elif available == 0:
                                self.notify("No stock available. Cannot add item.", severity="error")
                                return
                            else:
                                self.notify(
                                    f"Only {available} in stock. Quantity clamped to {available}.",
                                    severity="warning",
                                )
                                qty = available
                    self._items.append(MovementItemRow(int(pk), prod["ProductName"], qty))
                    self._refresh_items_table()

            self.app.push_screen(QtyModal(), callback=after_qty)

        self.app.push_screen(
            PickerModal(
                "Select Product",
                [("ID", 4), ("Product Name", 28), ("Category", 16), ("Price", 8), ("Stock", 6)],
                rows,
            ),
            callback=after_product,
        )

    @on(Button.Pressed, "#btn-rem-item")
    def on_remove_item(self) -> None:
        if self._selected_idx is not None and 0 <= self._selected_idx < len(self._items):
            self._items.pop(self._selected_idx)
            self._selected_idx = None
            self._refresh_items_table()
        else:
            self.notify("Select an item first.", severity="warning")

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        from datetime import datetime
        doc_date = self.query_one("#f-date", Input).value.strip()
        try:
            datetime.strptime(doc_date, "%Y-%m-%d")
        except ValueError:
            self.notify("Date must be YYYY-MM-DD.", severity="error")
            return
        if not self._items:
            self.notify("Add at least one item.", severity="error")
            return
        reason = self.query_one("#f-reason", Input).value.strip()
        items_data = [{"product_id": it.product_id, "quantity": it.quantity}
                      for it in self._items]
        try:
            if self.doc_type == "SI":
                doc_id = siso.create_si(doc_date, reason, items=items_data)
                self.notify(f"SI #{doc_id} created — stock increased.", severity="information")
            else:
                doc_id = siso.create_so(doc_date, reason, items=items_data)
                self.notify(f"SO #{doc_id} created — stock decreased.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class MovementDetailModal(ModalScreen):
    """View a SI or SO document's details."""

    def __init__(self, doc_type: str, doc_id: int) -> None:
        super().__init__()
        self.doc_type = doc_type
        self.doc_id = doc_id

    def compose(self) -> ComposeResult:
        with Vertical(classes="order-detail-dialog"):
            yield Label("", id="doc-title", classes="modal-title")
            yield Static("", id="doc-header")
            yield Label("Items:", classes="section-label")
            yield DataTable(id="items-tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="modal-buttons"):
                yield Button("Delete", id="btn-delete", variant="error")
                yield Button("Close",  id="btn-close")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        tbl = self.query_one("#items-tbl", DataTable)
        for label, width in [("Product Name", 36), ("Quantity", 10)]:
            tbl.add_column(label, width=width)
        self._load()

    def _load(self) -> None:
        if self.doc_type == "SI":
            hdr = siso.get_si_by_pk(self.doc_id)
            items = siso.fetch_si_items(self.doc_id)
            num_field = "SI_Number"
            date_field = "SI_Date"
        else:
            hdr = siso.get_so_by_pk(self.doc_id)
            items = siso.fetch_so_items(self.doc_id)
            num_field = "SO_Number"
            date_field = "SO_Date"
        if not hdr:
            self.dismiss(False)
            return
        self.query_one("#doc-title", Label).update(
            f"{self.doc_type} #{self.doc_id} — {hdr.get(num_field, '')}"
        )
        info = [
            f"[b]Number:[/b] {hdr.get(num_field, '')}",
            f"[b]Date:[/b]   {hdr.get(date_field, '')}",
            f"[b]Reason:[/b] {hdr.get('Reason') or '—'}",
        ]
        self.query_one("#doc-header", Static).update("\n".join(info))
        tbl = self.query_one("#items-tbl", DataTable)
        tbl.clear()
        for it in items:
            tbl.add_row(it["ProductName"], str(it["Quantity"]))

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        def after(confirmed):
            if confirmed:
                try:
                    if self.doc_type == "SI":
                        siso.delete_si(self.doc_id)
                    else:
                        siso.delete_so(self.doc_id)
                    self.notify("Document deleted.", severity="information")
                    self.dismiss(True)
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(
            ConfirmDeleteModal(f"{self.doc_type} #{self.doc_id}"), callback=after
        )

    @on(Button.Pressed, "#btn-close")
    def on_close(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class StockMovementsPanel(Widget):
    """Panel with two tabs: SI (goods in) and SO (goods out)."""

    BINDINGS = [
        ("n", "new_record",   "New"),
        ("f", "focus_search", "Search"),
    ]

    _si_selected: str | None = None
    _so_selected: str | None = None

    def compose(self) -> ComposeResult:
        with TabbedContent(id="mov-tabs"):
            with TabPane("SI — Stock In", id="tab-si"):
                with Vertical(classes="panel-container"):
                    yield DataTable(id="si-tbl", cursor_type="row", zebra_stripes=True)
                    with Horizontal(classes="toolbar"):
                        yield Button("+ New SI", id="btn-new-si", variant="success")
                        yield Button("Open",     id="btn-open-si")
                        yield Button("Delete",   id="btn-del-si", variant="error")
                        yield Label("", id="si-count", classes="count-label")
            with TabPane("SO — Stock Out", id="tab-so"):
                with Vertical(classes="panel-container"):
                    yield DataTable(id="so-tbl", cursor_type="row", zebra_stripes=True)
                    with Horizontal(classes="toolbar"):
                        yield Button("+ New SO", id="btn-new-so", variant="success")
                        yield Button("Open",     id="btn-open-so")
                        yield Button("Delete",   id="btn-del-so", variant="error")
                        yield Label("", id="so-count", classes="count-label")

    def on_mount(self) -> None:
        si_tbl = self.query_one("#si-tbl", DataTable)
        for label, width in [("ID", 6), ("Number", 16), ("Date", 12), ("Reason", 26), ("Qty", 6)]:
            si_tbl.add_column(label, width=width)

        so_tbl = self.query_one("#so-tbl", DataTable)
        for label, width in [("ID", 6), ("Number", 16), ("Date", 12), ("Reason", 26), ("Qty", 6)]:
            so_tbl.add_column(label, width=width)

        self._refresh_si()
        self._refresh_so()

    def _refresh_si(self) -> None:
        tbl = self.query_one("#si-tbl", DataTable)
        tbl.clear()
        rows = siso.fetch_all_si()
        for row in rows:
            tbl.add_row(*[str(c) if c is not None else "" for c in row], key=str(row[0]))
        try:
            self.query_one("#si-count", Label).update(f"{len(rows)} records")
        except Exception:
            pass

    def _refresh_so(self) -> None:
        tbl = self.query_one("#so-tbl", DataTable)
        tbl.clear()
        rows = siso.fetch_all_so()
        for row in rows:
            tbl.add_row(*[str(c) if c is not None else "" for c in row], key=str(row[0]))
        try:
            self.query_one("#so-count", Label).update(f"{len(rows)} records")
        except Exception:
            pass

    def refresh_data(self) -> None:
        self._refresh_si()
        self._refresh_so()

    @on(DataTable.RowHighlighted, "#si-tbl")
    def on_si_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._si_selected = event.row_key.value

    @on(DataTable.RowHighlighted, "#so-tbl")
    def on_so_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._so_selected = event.row_key.value

    @on(DataTable.RowSelected, "#si-tbl")
    def on_si_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key:
            self._open_detail("SI", int(event.row_key.value))

    @on(DataTable.RowSelected, "#so-tbl")
    def on_so_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key:
            self._open_detail("SO", int(event.row_key.value))

    def _open_detail(self, doc_type: str, doc_id: int) -> None:
        def after(changed):
            if changed:
                self._refresh_si()
                self._refresh_so()
        self.app.push_screen(MovementDetailModal(doc_type, doc_id), callback=after)

    @on(Button.Pressed, "#btn-new-si")
    def on_new_si(self) -> None:
        def after(saved):
            if saved:
                self._refresh_si()
        self.app.push_screen(MovementFormModal("SI"), callback=after)

    @on(Button.Pressed, "#btn-new-so")
    def on_new_so(self) -> None:
        def after(saved):
            if saved:
                self._refresh_so()
        self.app.push_screen(MovementFormModal("SO"), callback=after)

    @on(Button.Pressed, "#btn-open-si")
    def on_open_si(self) -> None:
        if self._si_selected:
            self._open_detail("SI", int(self._si_selected))
        else:
            self.notify("Select a SI document first.", severity="warning")

    @on(Button.Pressed, "#btn-open-so")
    def on_open_so(self) -> None:
        if self._so_selected:
            self._open_detail("SO", int(self._so_selected))
        else:
            self.notify("Select a SO document first.", severity="warning")

    @on(Button.Pressed, "#btn-del-si")
    def on_delete_si(self) -> None:
        if not self._si_selected:
            self.notify("Select a SI document first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    siso.delete_si(int(self._si_selected))
                    self._si_selected = None
                    self._refresh_si()
                    self.notify("SI deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"SI #{self._si_selected}"), callback=after)

    @on(Button.Pressed, "#btn-del-so")
    def on_delete_so(self) -> None:
        if not self._so_selected:
            self.notify("Select a SO document first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    siso.delete_so(int(self._so_selected))
                    self._so_selected = None
                    self._refresh_so()
                    self.notify("SO deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"SO #{self._so_selected}"), callback=after)

    def action_new_record(self) -> None:
        # Determine active tab
        try:
            active = self.query_one(TabbedContent).active
            doc_type = "SO" if active == "tab-so" else "SI"
        except Exception:
            doc_type = "SI"
        def after(saved):
            if saved:
                self._refresh_si()
                self._refresh_so()
        self.app.push_screen(MovementFormModal(doc_type), callback=after)

    def action_focus_search(self) -> None:
        pass  # No search box in this panel
