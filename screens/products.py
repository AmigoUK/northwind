"""screens/products.py — Products panel, detail modal, and form modal."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static, Switch
from textual import on

import data.products as pdata
from data.settings import get_currency_symbol
import data.categories as cdata
import data.suppliers as sdata
from screens.modals import ConfirmDeleteModal, PickerModal


class ProductFormModal(ModalScreen):
    def __init__(self, pk=None, category_id=None, supplier_id=None) -> None:
        super().__init__()
        self.pk = pk
        self._category_id = category_id
        self._supplier_id = supplier_id

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(
                "Add Product" if not self.pk else f"Edit Product #{self.pk}",
                classes="modal-title",
            )
            yield Label("Product Name *:")
            yield Input(id="f-name", placeholder="Product Name")
            yield Label("Quantity Per Unit:")
            yield Input(id="f-qty", placeholder="e.g. 10 boxes x 20 bags")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Unit Price:")
                    yield Input(id="f-price", placeholder="0.00")
                with Vertical(classes="form-field"):
                    yield Label("Units In Stock:")
                    yield Input(id="f-stock", placeholder="0")
                with Vertical(classes="form-field"):
                    yield Label("Reorder Level:")
                    yield Input(id="f-reord", placeholder="0")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Units On Order:")
                    yield Input(id="f-order", placeholder="0")
                with Vertical(classes="form-field"):
                    yield Label("Discontinued:")
                    yield Switch(id="sw-discontinued", value=False)
            yield Label("Category:")
            with Horizontal():
                yield Label("(none)", id="lbl-category")
                yield Button("Pick Category ▼", id="btn-pick-cat")
            yield Label("Supplier:")
            with Horizontal():
                yield Label("(none)", id="lbl-supplier")
                yield Button("Pick Supplier ▼", id="btn-pick-sup")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        if self.pk:
            row = pdata.get_by_pk(self.pk)
            if row:
                self.query_one("#f-name",  Input).value = row.get("ProductName")    or ""
                self.query_one("#f-qty",   Input).value = row.get("QuantityPerUnit") or ""
                self.query_one("#f-price", Input).value = str(row.get("UnitPrice", 0.0))
                self.query_one("#f-stock", Input).value = str(row.get("UnitsInStock", 0))
                self.query_one("#f-order", Input).value = str(row.get("UnitsOnOrder", 0))
                self.query_one("#f-reord", Input).value = str(row.get("ReorderLevel", 0))
                self.query_one("#sw-discontinued", Switch).value = bool(row.get("Discontinued"))
                self._category_id = row.get("CategoryID")
                self._supplier_id = row.get("SupplierID")
        # Set label text for pre-selected FKs
        if self._category_id:
            cat = cdata.get_by_pk(self._category_id)
            if cat:
                self.query_one("#lbl-category", Label).update(cat["CategoryName"])
        if self._supplier_id:
            sup = sdata.get_by_pk(self._supplier_id)
            if sup:
                self.query_one("#lbl-supplier", Label).update(sup["CompanyName"])

    @on(Button.Pressed, "#btn-pick-cat")
    def on_pick_category(self) -> None:
        rows = cdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._category_id = int(pk)
                cat = cdata.get_by_pk(int(pk))
                if cat:
                    self.query_one("#lbl-category", Label).update(cat["CategoryName"])
        self.app.push_screen(
            PickerModal("Select Category", [("ID", 4), ("Name", 22), ("Description", 38)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-pick-sup")
    def on_pick_supplier(self) -> None:
        rows = sdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._supplier_id = int(pk)
                sup = sdata.get_by_pk(int(pk))
                if sup:
                    self.query_one("#lbl-supplier", Label).update(sup["CompanyName"])
        self.app.push_screen(
            PickerModal("Select Supplier", [("ID", 4), ("Company", 28), ("City", 14), ("Country", 12)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        name = self.query_one("#f-name", Input).value.strip()
        if not name:
            self.notify("Product Name is required.", severity="error")
            return

        try:
            price = float(self.query_one("#f-price", Input).value.strip() or "0")
        except ValueError:
            self.notify("Unit Price must be a number.", severity="error")
            return

        try:
            stock = int(self.query_one("#f-stock", Input).value.strip() or "0")
            order = int(self.query_one("#f-order", Input).value.strip() or "0")
            reord = int(self.query_one("#f-reord", Input).value.strip() or "0")
        except ValueError:
            self.notify("Stock/Order/Reorder fields must be integers.", severity="error")
            return

        data = {
            "ProductName":    name,
            "QuantityPerUnit": self.query_one("#f-qty", Input).value.strip(),
            "UnitPrice":      price,
            "UnitsInStock":   stock,
            "UnitsOnOrder":   order,
            "ReorderLevel":   reord,
            "Discontinued":   self.query_one("#sw-discontinued", Switch).value,
            "CategoryID":     self._category_id,
            "SupplierID":     self._supplier_id,
        }
        try:
            if self.pk is None:
                pdata.insert(data)
                self.notify(f"Product '{name}' added.", severity="information")
            else:
                old_row = pdata.get_by_pk(self.pk)
                old_stock = old_row.get("UnitsInStock", 0) if old_row else 0
                pdata.update(self.pk, data)
                delta = stock - old_stock
                if delta != 0:
                    from data.si_so import record_stock_audit
                    record_stock_audit("SI" if delta > 0 else "SO", self.pk, abs(delta))
                self.notify("Product updated.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class ProductDetailModal(ModalScreen):
    def __init__(self, pk) -> None:
        super().__init__()
        self.pk = pk
        self._changed = False

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("", id="detail-title", classes="modal-title")
            yield Static("", id="detail-content")
            with Horizontal(classes="modal-buttons"):
                yield Button("Edit",   id="btn-edit",   variant="primary")
                yield Button("Delete", id="btn-delete", variant="error")
                yield Button("Close",  id="btn-close")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        self._load()

    def _load(self) -> None:
        sym = get_currency_symbol()
        row = pdata.get_by_pk(self.pk)
        if not row:
            self.dismiss(self._changed)
            return
        self.query_one("#detail-title", Label).update(f"Product #{self.pk}: {row['ProductName']}")
        lines = [
            f"[b]ID:[/b]             {row['ProductID']}",
            f"[b]Name:[/b]           {row.get('ProductName') or ''}",
            f"[b]Category:[/b]       #{row.get('CategoryID', '')} {row.get('CategoryName') or ''}",
            f"[b]Supplier:[/b]       #{row.get('SupplierID', '')} {row.get('SupplierName') or ''}",
            f"[b]Qty Per Unit:[/b]   {row.get('QuantityPerUnit') or ''}",
            f"[b]Unit Price:[/b]     {sym}{row.get('UnitPrice', 0.0):.2f}",
            f"[b]Units In Stock:[/b] {row.get('UnitsInStock', 0)}",
            f"[b]Units On Order:[/b] {row.get('UnitsOnOrder', 0)}",
            f"[b]Reorder Level:[/b]  {row.get('ReorderLevel', 0)}",
            f"[b]Discontinued:[/b]   {'Yes' if row.get('Discontinued') else 'No'}",
        ]
        self.query_one("#detail-content", Static).update("\n".join(lines))

    @on(Button.Pressed, "#btn-edit")
    def on_edit(self) -> None:
        def after(saved):
            if saved:
                self._changed = True
                self._load()
        self.app.push_screen(ProductFormModal(pk=self.pk), callback=after)

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        row = pdata.get_by_pk(self.pk)
        name = row.get("ProductName", str(self.pk)) if row else str(self.pk)

        def after_confirm(confirmed):
            if confirmed:
                try:
                    pdata.delete(self.pk)
                    self.dismiss(True)
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")

        self.app.push_screen(ConfirmDeleteModal(name), callback=after_confirm)

    @on(Button.Pressed, "#btn-close")
    def on_close(self) -> None:
        self.dismiss(self._changed)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(self._changed)


class ProductsPanel(Widget):
    BINDINGS = [
        ("n", "new_record",   "New Product"),
        ("f", "focus_search", "Search"),
        ("l", "low_stock",    "Low Stock"),
        ("x", "export_csv",   "Export CSV"),
    ]

    _selected_pk = None
    _low_stock_mode: bool = False

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Input(placeholder="Search products...", id="search-box")
            yield DataTable(id="tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("+ New",      id="btn-new",    variant="success")
                yield Button("Open",       id="btn-open")
                yield Button("Delete",     id="btn-delete", variant="error")
                yield Button("Low Stock",  id="btn-low")
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        for label, width in [
            ("ID", 4), ("Product Name", 25), ("Category", 14),
            ("Supplier", 20), ("Price", 7), ("In Stock", 8), ("Discontinued", 11),
        ]:
            tbl.add_column(label, width=width)
        self.refresh_data()

    def refresh_data(self, term: str = "") -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        rows = pdata.search(term) if term else pdata.fetch_all()
        for row in rows:
            tbl.add_row(*[str(c) if c is not None else "" for c in row],
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
            self._open_detail(event.row_key.value)

    def _open_detail(self, pk) -> None:
        def after(changed):
            if changed:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(ProductDetailModal(pk=int(pk)), callback=after)

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-open")
    def on_btn_open(self) -> None:
        if self._selected_pk:
            self._open_detail(self._selected_pk)
        else:
            self.notify("Select a product first.", severity="warning")

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        if not self._selected_pk:
            self.notify("Select a product first.", severity="warning")
            return
        row = pdata.get_by_pk(int(self._selected_pk))
        name = row.get("ProductName", str(self._selected_pk)) if row else str(self._selected_pk)

        def after_confirm(confirmed):
            if confirmed:
                try:
                    pdata.delete(int(self._selected_pk))
                    self._selected_pk = None
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify("Product deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")

        self.app.push_screen(ConfirmDeleteModal(name), callback=after_confirm)

    @on(Button.Pressed, "#btn-low")
    def on_btn_low(self) -> None:
        self.action_low_stock()

    def action_new_record(self) -> None:
        def after(saved):
            if saved:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(ProductFormModal(pk=None), callback=after)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()

    def action_export_csv(self) -> None:
        import csv, os
        from datetime import datetime
        term = self.query_one("#search-box", Input).value
        rows = pdata.search(term) if term else pdata.fetch_all()
        headers = ["ID", "Product Name", "Category", "Supplier", "Price", "In Stock", "Discontinued"]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.expanduser(f"~/Downloads/northwind_products_{ts}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([str(c) if c is not None else "" for c in row])
        self.notify(f"Exported {len(rows)} rows → {path}", severity="information")

    def action_low_stock(self) -> None:
        self._low_stock_mode = not self._low_stock_mode
        btn = self.query_one("#btn-low", Button)
        if self._low_stock_mode:
            tbl = self.query_one(DataTable)
            tbl.clear()
            rows = pdata.low_stock()
            if not rows:
                self._low_stock_mode = False
                btn.label = "Low Stock"
                self.notify("No low-stock products found.", severity="information")
                return
            for row in rows:
                tbl.add_row(*[str(c) if c is not None else "" for c in row],
                            key=str(row[0]))
            btn.label = "Show All"
            self.notify(f"Showing {len(rows)} low-stock product(s).", severity="warning")
        else:
            btn.label = "Low Stock"
            self.refresh_data(self.query_one("#search-box", Input).value)
