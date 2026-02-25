from __future__ import annotations
"""screens/orders.py — Orders panel, detail, form, and line-item modals."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static
from textual import on

import data.orders as odata
from data.settings import get_currency_symbol
import data.customers as cdata
import data.employees as edata
import data.shippers as shdata
import data.products as pdata
from screens.modals import ConfirmDeleteModal, PickerModal


class ShipOrderModal(ModalScreen):
    """Small modal to capture a shipped date."""

    def __init__(self, order_id: int) -> None:
        super().__init__()
        self.order_id = order_id

    def compose(self) -> ComposeResult:
        with Vertical(classes="confirm-dialog"):
            yield Label(f"Mark Order #{self.order_id} as Shipped", classes="modal-title")
            yield Label("Shipped Date (YYYY-MM-DD):")
            yield Input(id="f-date", placeholder="1996-07-20")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        from datetime import date
        self.query_one("#f-date", Input).value = str(date.today())

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        from datetime import datetime
        val = self.query_one("#f-date", Input).value.strip()
        if not val:
            self.notify("Shipped date is required.", severity="error")
            return
        try:
            datetime.strptime(val, "%Y-%m-%d")
        except ValueError:
            self.notify("Date must be YYYY-MM-DD.", severity="error")
            return
        try:
            odata.mark_shipped(self.order_id, val)
            self.notify(f"Order #{self.order_id} marked as shipped.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class LineItemFormModal(ModalScreen):
    """Add a single line item to an order."""

    def __init__(self, order_id: int) -> None:
        super().__init__()
        self.order_id = order_id
        self._product_id = None
        self._product_name = ""

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(f"Add Item to Order #{self.order_id}", classes="modal-title")
            yield Label("Product:")
            with Horizontal():
                yield Label("(none)", id="lbl-product")
                yield Button("Pick Product", id="btn-pick-prod")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Unit Price:")
                    yield Input(id="f-price", placeholder="0.00")
                with Vertical(classes="form-field"):
                    yield Label("Quantity:")
                    yield Input(id="f-qty", value="1", placeholder="1")
                with Vertical(classes="form-field"):
                    yield Label("Discount (0.00 - 1.00):")
                    yield Input(id="f-disc", value="0.00", placeholder="0.00")
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
                    self.query_one("#f-price", Input).value = str(prod.get("UnitPrice", 0.0))
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
            price = float(self.query_one("#f-price", Input).value.strip() or "0")
            qty   = int(self.query_one("#f-qty",   Input).value.strip() or "1")
            disc  = float(self.query_one("#f-disc", Input).value.strip() or "0")
        except ValueError:
            self.notify("Price/Qty/Discount must be numbers.", severity="error")
            return
        if qty < 1:
            self.notify("Quantity must be at least 1.", severity="error")
            return
        disc = max(0.0, min(1.0, disc))
        try:
            odata.add_line_item(self.order_id, self._product_id, price, qty, disc)
            self.notify(f"'{self._product_name}' added to order.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class OrderFormModal(ModalScreen):
    """Create a new order header. Dismisses with new order_id (int) or None."""

    def __init__(self, customer_id: str | None = None) -> None:
        super().__init__()
        self._customer_id = customer_id
        self._employee_id = None
        self._shipper_id = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("Create New Order", classes="modal-title")
            yield Label("Customer *:")
            with Horizontal():
                yield Label(self._customer_id or "(none)", id="lbl-customer")
                yield Button("Pick Customer", id="btn-pick-cust")
            yield Label("Employee:")
            with Horizontal():
                yield Label("(none)", id="lbl-employee")
                yield Button("Pick Employee", id="btn-pick-emp")
            yield Label("Shipper:")
            with Horizontal():
                yield Label("(none)", id="lbl-shipper")
                yield Button("Pick Shipper", id="btn-pick-ship")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Order Date (YYYY-MM-DD):")
                    yield Input(id="f-orderdate", placeholder="1996-07-04")
                with Vertical(classes="form-field"):
                    yield Label("Required Date (YYYY-MM-DD):")
                    yield Input(id="f-reqdate", placeholder="1996-08-01")
                with Vertical(classes="form-field"):
                    yield Label("Freight:")
                    yield Input(id="f-freight", value="0.00", placeholder="0.00")
            yield Label("Ship Name:")
            yield Input(id="f-shipname", placeholder="Ship Name")
            yield Label("Ship Address:")
            yield Input(id="f-shipaddr", placeholder="Ship Address")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Ship City:")
                    yield Input(id="f-shipcity", placeholder="Ship City")
                with Vertical(classes="form-field"):
                    yield Label("Ship Region:")
                    yield Input(id="f-shipreg", placeholder="Ship Region")
                with Vertical(classes="form-field"):
                    yield Label("Ship Postal Code:")
                    yield Input(id="f-shippost", placeholder="Ship Postal Code")
            yield Label("Ship Country:")
            yield Input(id="f-shipcntry", placeholder="Ship Country")
            with Horizontal(classes="modal-buttons"):
                yield Button("Create Order", id="btn-save", variant="primary")
                yield Button("Cancel",       id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        from datetime import date
        self.query_one("#f-orderdate", Input).value = str(date.today())
        if self._customer_id:
            cust = cdata.get_by_pk(self._customer_id)
            if cust:
                self.query_one("#lbl-customer",  Label).update(cust["CompanyName"])
                self.query_one("#f-shipname",    Input).value = cust.get("CompanyName") or ""
                self.query_one("#f-shipaddr",    Input).value = cust.get("Address")     or ""
                self.query_one("#f-shipcity",    Input).value = cust.get("City")        or ""
                self.query_one("#f-shipreg",     Input).value = cust.get("Region")      or ""
                self.query_one("#f-shippost",    Input).value = cust.get("PostalCode")  or ""
                self.query_one("#f-shipcntry",   Input).value = cust.get("Country")     or ""

    @on(Button.Pressed, "#btn-pick-cust")
    def on_pick_customer(self) -> None:
        rows = cdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._customer_id = pk
                cust = cdata.get_by_pk(pk)
                if cust:
                    self.query_one("#lbl-customer", Label).update(cust["CompanyName"])
                    self.query_one("#f-shipname",   Input).value = cust.get("CompanyName") or ""
                    self.query_one("#f-shipaddr",   Input).value = cust.get("Address")     or ""
                    self.query_one("#f-shipcity",   Input).value = cust.get("City")        or ""
                    self.query_one("#f-shipreg",    Input).value = cust.get("Region")      or ""
                    self.query_one("#f-shippost",   Input).value = cust.get("PostalCode")  or ""
                    self.query_one("#f-shipcntry",  Input).value = cust.get("Country")     or ""
        self.app.push_screen(
            PickerModal("Select Customer", [("ID", 6), ("Company", 26), ("Contact", 18), ("City", 12)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-pick-emp")
    def on_pick_employee(self) -> None:
        rows = edata.fetch_for_picker()
        def after(pk):
            if pk:
                self._employee_id = int(pk)
                emp = edata.get_by_pk(int(pk))
                if emp:
                    self.query_one("#lbl-employee", Label).update(
                        f"{emp['FirstName']} {emp['LastName']}"
                    )
        self.app.push_screen(
            PickerModal("Select Employee", [("ID", 4), ("Name", 26), ("Title", 28)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-pick-ship")
    def on_pick_shipper(self) -> None:
        rows = shdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._shipper_id = int(pk)
                ship = shdata.get_by_pk(int(pk))
                if ship:
                    self.query_one("#lbl-shipper", Label).update(ship["CompanyName"])
        self.app.push_screen(
            PickerModal("Select Shipper", [("ID", 4), ("Company", 30), ("Phone", 20)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        from datetime import datetime
        if not self._customer_id:
            self.notify("Customer is required.", severity="error")
            return

        orderdate = self.query_one("#f-orderdate", Input).value.strip()
        reqdate   = self.query_one("#f-reqdate",   Input).value.strip()
        for label, val in [("Order Date", orderdate), ("Required Date", reqdate)]:
            if val:
                try:
                    datetime.strptime(val, "%Y-%m-%d")
                except ValueError:
                    self.notify(f"{label} must be YYYY-MM-DD.", severity="error")
                    return

        try:
            freight = float(self.query_one("#f-freight", Input).value.strip() or "0")
        except ValueError:
            self.notify("Freight must be a number.", severity="error")
            return

        data = {
            "CustomerID":     self._customer_id,
            "EmployeeID":     self._employee_id,
            "OrderDate":      orderdate or None,
            "RequiredDate":   reqdate or None,
            "ShipVia":        self._shipper_id,
            "Freight":        freight,
            "ShipName":       self.query_one("#f-shipname",  Input).value.strip(),
            "ShipAddress":    self.query_one("#f-shipaddr",  Input).value.strip(),
            "ShipCity":       self.query_one("#f-shipcity",  Input).value.strip(),
            "ShipRegion":     self.query_one("#f-shipreg",   Input).value.strip(),
            "ShipPostalCode": self.query_one("#f-shippost",  Input).value.strip(),
            "ShipCountry":    self.query_one("#f-shipcntry", Input).value.strip(),
        }
        try:
            order_id = odata.insert_header(data)
            self.notify(f"Order #{order_id} created.", severity="information")
            self.dismiss(order_id)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class OrderDetailModal(ModalScreen):
    """Full order detail with line items table. Dismisses with True if anything changed."""

    def __init__(self, order_id: int) -> None:
        super().__init__()
        self.order_id = order_id
        self._changed = False
        self._selected_product_id = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="order-detail-dialog"):
            yield Label("", id="order-title", classes="modal-title")
            yield Static("", id="order-header")
            yield Label("Line Items:", classes="section-label")
            yield DataTable(id="lines-tbl", cursor_type="row", zebra_stripes=True)
            yield Static("", id="order-totals")
            with Horizontal(classes="modal-buttons"):
                yield Button("Edit Header", id="btn-edit",   variant="default")
                yield Button("Ship",        id="btn-ship",   variant="default")
                yield Button("+ Item",      id="btn-add",    variant="success")
                yield Button("- Item",      id="btn-remove", variant="warning")
                yield Button("Delete",      id="btn-delete", variant="error")
                yield Button("Close",       id="btn-close")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        tbl = self.query_one("#lines-tbl", DataTable)
        for label, width in [
            ("ProdID", 6), ("Product Name", 24), ("Qty", 5),
            ("Unit Price", 10), ("Disc%", 6), ("Line Total", 10),
        ]:
            tbl.add_column(label, width=width)
        self._load()

    def _load(self) -> None:
        sym = get_currency_symbol()
        hdr = odata.get_by_pk(self.order_id)
        if not hdr:
            self.dismiss(self._changed)
            return

        self.query_one("#order-title", Label).update(f"Order #{self.order_id}")

        header_lines = [
            f"[b]Customer:[/b]   {hdr.get('CustomerID', '')} — {hdr.get('CompanyName') or ''}",
            f"[b]Employee:[/b]   {hdr.get('EmployeeName') or '(none)'}",
            f"[b]Order Date:[/b] {hdr.get('OrderDate') or ''}   "
            f"[b]Required:[/b] {hdr.get('RequiredDate') or ''}   "
            f"[b]Shipped:[/b] {hdr.get('ShippedDate') or '(pending)'}",
            f"[b]Ship Via:[/b]   {hdr.get('ShipperName') or '(none)'}",
            f"[b]Ship To:[/b]    {hdr.get('ShipName') or ''}, "
            f"{hdr.get('ShipCity') or ''}, {hdr.get('ShipCountry') or ''}",
        ]
        self.query_one("#order-header", Static).update("\n".join(header_lines))

        # Line items
        tbl = self.query_one("#lines-tbl", DataTable)
        tbl.clear()
        lines = odata.fetch_lines(self.order_id)
        for ln in lines:
            tbl.add_row(
                str(ln["ProductID"]),
                ln["ProductName"],
                str(ln["Quantity"]),
                f"{sym}{ln['UnitPrice']:.2f}",
                f"{ln['Discount']*100:.0f}%",
                f"{sym}{ln['LineTotal']:.2f}",
                key=str(ln["ProductID"]),
            )

        # Totals
        totals = odata.fetch_totals(self.order_id)
        if totals:
            subtotal = totals["subtotal"]
            freight  = totals["Freight"] or 0.0
            grand    = subtotal + freight
            totals_text = (
                f"[b]Subtotal:[/b]    {sym}{subtotal:>10.2f}\n"
                f"[b]Freight:[/b]     {sym}{freight:>10.2f}\n"
                f"[b]GRAND TOTAL:[/b] {sym}{grand:>9.2f}"
            )
            self.query_one("#order-totals", Static).update(totals_text)

    @on(DataTable.RowHighlighted, "#lines-tbl")
    def on_line_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._selected_product_id = event.row_key.value

    @on(Button.Pressed, "#btn-edit")
    def on_edit_header(self) -> None:
        def after(saved):
            if saved:
                self._changed = True
                self._load()
        self.app.push_screen(OrderHeaderEditModal(self.order_id), callback=after)

    @on(Button.Pressed, "#btn-ship")
    def on_ship(self) -> None:
        hdr = odata.get_by_pk(self.order_id)
        if hdr and hdr.get("ShippedDate"):
            self.notify(f"Already shipped on {hdr['ShippedDate']}.", severity="warning")
            return
        def after(saved):
            if saved:
                self._changed = True
                self._load()
        self.app.push_screen(ShipOrderModal(self.order_id), callback=after)

    @on(Button.Pressed, "#btn-add")
    def on_add_item(self) -> None:
        def after(saved):
            if saved:
                self._changed = True
                self._load()
        self.app.push_screen(LineItemFormModal(self.order_id), callback=after)

    @on(Button.Pressed, "#btn-remove")
    def on_remove_item(self) -> None:
        if not self._selected_product_id:
            self.notify("Select a line item first.", severity="warning")
            return
        prod = pdata.get_by_pk(int(self._selected_product_id))
        name = prod.get("ProductName", f"#{self._selected_product_id}") if prod else f"#{self._selected_product_id}"

        def after_confirm(confirmed):
            if confirmed:
                try:
                    odata.remove_line_item(self.order_id, int(self._selected_product_id))
                    self._selected_product_id = None
                    self._changed = True
                    self._load()
                    self.notify("Line item removed.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot remove: {e}", severity="error")

        self.app.push_screen(ConfirmDeleteModal(f"line item: {name}"), callback=after_confirm)

    @on(Button.Pressed, "#btn-delete")
    def on_delete_order(self) -> None:
        def after_confirm(confirmed):
            if confirmed:
                try:
                    odata.delete(self.order_id)
                    self.dismiss(True)
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")

        self.app.push_screen(
            ConfirmDeleteModal(f"Order #{self.order_id}"), callback=after_confirm
        )

    @on(Button.Pressed, "#btn-close")
    def on_close(self) -> None:
        self.dismiss(self._changed)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(self._changed)


class OrderHeaderEditModal(ModalScreen):
    """Edit the header of an existing order."""

    def __init__(self, order_id: int) -> None:
        super().__init__()
        self.order_id = order_id
        self._shipper_id = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(f"Edit Order #{self.order_id} Header", classes="modal-title")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Order Date (YYYY-MM-DD):")
                    yield Input(id="f-orderdate", placeholder="1996-07-04")
                with Vertical(classes="form-field"):
                    yield Label("Required Date (YYYY-MM-DD):")
                    yield Input(id="f-reqdate", placeholder="1996-08-01")
                with Vertical(classes="form-field"):
                    yield Label("Freight:")
                    yield Input(id="f-freight", placeholder="0.00")
            yield Label("Shipper:")
            with Horizontal():
                yield Label("(current)", id="lbl-shipper")
                yield Button("Change Shipper", id="btn-pick-ship")
            yield Label("Ship Name:")
            yield Input(id="f-shipname", placeholder="Ship Name")
            yield Label("Ship Address:")
            yield Input(id="f-shipaddr", placeholder="Ship Address")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Ship City:")
                    yield Input(id="f-shipcity", placeholder="Ship City")
                with Vertical(classes="form-field"):
                    yield Label("Ship Region:")
                    yield Input(id="f-shipreg", placeholder="Ship Region")
                with Vertical(classes="form-field"):
                    yield Label("Ship Postal Code:")
                    yield Input(id="f-shippost", placeholder="Ship Postal Code")
            yield Label("Ship Country:")
            yield Input(id="f-shipcntry", placeholder="Ship Country")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save",   id="btn-save",   variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        row = odata.get_by_pk(self.order_id)
        if row:
            self.query_one("#f-orderdate", Input).value = row.get("OrderDate")      or ""
            self.query_one("#f-reqdate",   Input).value = row.get("RequiredDate")   or ""
            self.query_one("#f-freight",   Input).value = str(row.get("Freight", 0.0))
            self.query_one("#f-shipname",  Input).value = row.get("ShipName")       or ""
            self.query_one("#f-shipaddr",  Input).value = row.get("ShipAddress")    or ""
            self.query_one("#f-shipcity",  Input).value = row.get("ShipCity")       or ""
            self.query_one("#f-shipreg",   Input).value = row.get("ShipRegion")     or ""
            self.query_one("#f-shippost",  Input).value = row.get("ShipPostalCode") or ""
            self.query_one("#f-shipcntry", Input).value = row.get("ShipCountry")    or ""
            self._shipper_id = row.get("ShipVia")
            if row.get("ShipperName"):
                self.query_one("#lbl-shipper", Label).update(row["ShipperName"])

    @on(Button.Pressed, "#btn-pick-ship")
    def on_pick_shipper(self) -> None:
        rows = shdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._shipper_id = int(pk)
                ship = shdata.get_by_pk(int(pk))
                if ship:
                    self.query_one("#lbl-shipper", Label).update(ship["CompanyName"])
        self.app.push_screen(
            PickerModal("Select Shipper", [("ID", 4), ("Company", 30), ("Phone", 20)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        from datetime import datetime
        orderdate = self.query_one("#f-orderdate", Input).value.strip()
        reqdate   = self.query_one("#f-reqdate",   Input).value.strip()
        for label, val in [("Order Date", orderdate), ("Required Date", reqdate)]:
            if val:
                try:
                    datetime.strptime(val, "%Y-%m-%d")
                except ValueError:
                    self.notify(f"{label} must be YYYY-MM-DD.", severity="error")
                    return
        try:
            freight = float(self.query_one("#f-freight", Input).value.strip() or "0")
        except ValueError:
            self.notify("Freight must be a number.", severity="error")
            return

        data = {
            "OrderDate":      orderdate or None,
            "RequiredDate":   reqdate or None,
            "ShipVia":        self._shipper_id,
            "Freight":        freight,
            "ShipName":       self.query_one("#f-shipname",  Input).value.strip(),
            "ShipAddress":    self.query_one("#f-shipaddr",  Input).value.strip(),
            "ShipCity":       self.query_one("#f-shipcity",  Input).value.strip(),
            "ShipRegion":     self.query_one("#f-shipreg",   Input).value.strip(),
            "ShipPostalCode": self.query_one("#f-shippost",  Input).value.strip(),
            "ShipCountry":    self.query_one("#f-shipcntry", Input).value.strip(),
        }
        try:
            odata.update_header(self.order_id, data)
            self.notify("Order header updated.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class OrdersPanel(Widget):
    BINDINGS = [
        ("n", "new_record",   "New Order"),
        ("f", "focus_search", "Search"),
        ("+", "add_item",     "Add Item"),
        ("x", "export_csv",   "Export CSV"),
    ]

    _selected_pk = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Input(placeholder="Search orders...", id="search-box")
            yield DataTable(id="tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("+ New",  id="btn-new",    variant="success")
                yield Button("Open",   id="btn-open")
                yield Button("Delete", id="btn-delete", variant="error")
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        for label, width in [
            ("ID", 6), ("Customer", 25), ("Employee", 20),
            ("Order Date", 12), ("Shipped", 12), ("Total", 10),
        ]:
            tbl.add_column(label, width=width)
        self.refresh_data()

    def refresh_data(self, term: str = "") -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        rows = odata.search(term) if term else odata.fetch_all()
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
            self._open_detail(int(event.row_key.value))

    def _open_detail(self, order_id: int) -> None:
        def after(changed):
            if changed:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(OrderDetailModal(order_id), callback=after)

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-open")
    def on_btn_open(self) -> None:
        if self._selected_pk:
            self._open_detail(int(self._selected_pk))
        else:
            self.notify("Select an order first.", severity="warning")

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        if not self._selected_pk:
            self.notify("Select an order first.", severity="warning")
            return

        def after_confirm(confirmed):
            if confirmed:
                try:
                    odata.delete(int(self._selected_pk))
                    self._selected_pk = None
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify("Order deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")

        self.app.push_screen(
            ConfirmDeleteModal(f"Order #{self._selected_pk}"), callback=after_confirm
        )

    def action_new_record(self) -> None:
        def after_form(order_id):
            if order_id:
                def after_detail(result):
                    self.refresh_data(self.query_one("#search-box", Input).value)
                self.app.push_screen(OrderDetailModal(order_id), callback=after_detail)
        self.app.push_screen(OrderFormModal(), callback=after_form)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()

    def action_export_csv(self) -> None:
        import csv, os
        from datetime import datetime
        term = self.query_one("#search-box", Input).value
        rows = odata.search(term) if term else odata.fetch_all()
        headers = ["ID", "Customer", "Employee", "Order Date", "Shipped", "Total"]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.expanduser(f"~/Downloads/northwind_orders_{ts}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([str(c) if c is not None else "" for c in row])
        self.notify(f"Exported {len(rows)} rows → {path}", severity="information")

    def action_add_item(self) -> None:
        if not self._selected_pk:
            self.notify("Select an order first.", severity="warning")
            return
        def after(saved):
            if saved:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(LineItemFormModal(int(self._selected_pk)), callback=after)
