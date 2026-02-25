from __future__ import annotations
"""screens/customers.py — Customers panel, detail modal, and form modal."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static
from textual import on

import data.customers as cdata
from screens.modals import ConfirmDeleteModal, PickerModal


class CustomerFormModal(ModalScreen):
    """Add (pk=None) or edit (pk=str) a customer. Dismisses with True on save."""

    def __init__(self, pk: str | None = None) -> None:
        super().__init__()
        self.pk = pk

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(
                "Add Customer" if not self.pk else f"Edit Customer: {self.pk}",
                classes="modal-title",
            )
            if not self.pk:
                yield Label("Customer ID (5 chars):")
                yield Input(id="f-id", max_length=5, placeholder="CSTMR")
            yield Label("Company Name *:")
            yield Input(id="f-company", placeholder="Company Name")
            yield Label("Contact Name:")
            yield Input(id="f-contact", placeholder="Contact Name")
            yield Label("Contact Title:")
            yield Input(id="f-title", placeholder="Contact Title")
            yield Label("Address:")
            yield Input(id="f-address", placeholder="Address")
            yield Label("City:")
            yield Input(id="f-city", placeholder="City")
            yield Label("Region:")
            yield Input(id="f-region", placeholder="Region")
            yield Label("Postal Code:")
            yield Input(id="f-postal", placeholder="Postal Code")
            yield Label("Country:")
            yield Input(id="f-country", placeholder="Country")
            yield Label("Phone:")
            yield Input(id="f-phone", placeholder="Phone")
            yield Label("Fax:")
            yield Input(id="f-fax", placeholder="Fax")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        if self.pk:
            row = cdata.get_by_pk(self.pk)
            if row:
                self.query_one("#f-company", Input).value = row.get("CompanyName") or ""
                self.query_one("#f-contact", Input).value = row.get("ContactName") or ""
                self.query_one("#f-title",   Input).value = row.get("ContactTitle") or ""
                self.query_one("#f-address", Input).value = row.get("Address") or ""
                self.query_one("#f-city",    Input).value = row.get("City") or ""
                self.query_one("#f-region",  Input).value = row.get("Region") or ""
                self.query_one("#f-postal",  Input).value = row.get("PostalCode") or ""
                self.query_one("#f-country", Input).value = row.get("Country") or ""
                self.query_one("#f-phone",   Input).value = row.get("Phone") or ""
                self.query_one("#f-fax",     Input).value = row.get("Fax") or ""

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        company = self.query_one("#f-company", Input).value.strip()
        if not company:
            self.notify("Company Name is required.", severity="error")
            return
        data = {
            "CompanyName":  company,
            "ContactName":  self.query_one("#f-contact", Input).value.strip(),
            "ContactTitle": self.query_one("#f-title",   Input).value.strip(),
            "Address":      self.query_one("#f-address", Input).value.strip(),
            "City":         self.query_one("#f-city",    Input).value.strip(),
            "Region":       self.query_one("#f-region",  Input).value.strip(),
            "PostalCode":   self.query_one("#f-postal",  Input).value.strip(),
            "Country":      self.query_one("#f-country", Input).value.strip(),
            "Phone":        self.query_one("#f-phone",   Input).value.strip(),
            "Fax":          self.query_one("#f-fax",     Input).value.strip(),
        }
        try:
            if self.pk is None:
                cid = self.query_one("#f-id", Input).value.strip().upper()
                if len(cid) != 5:
                    self.notify("Customer ID must be exactly 5 characters.", severity="error")
                    return
                cdata.insert(cid, data)
                self.notify(f"Customer '{company}' added.", severity="information")
            else:
                cdata.update(self.pk, data)
                self.notify("Customer updated.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class CustomerDetailModal(ModalScreen):
    """Read-only detail view. Dismisses with True if a record was changed."""

    def __init__(self, pk: str) -> None:
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

    def on_mount(self) -> None:
        self._load()

    def _load(self) -> None:
        row = cdata.get_by_pk(self.pk)
        if not row:
            self.dismiss(self._changed)
            return
        self.query_one("#detail-title", Label).update(f"Customer: {row['CompanyName']}")
        lines = [
            f"[b]ID:[/b]            {row['CustomerID']}",
            f"[b]Company:[/b]       {row.get('CompanyName') or ''}",
            f"[b]Contact:[/b]       {row.get('ContactName') or ''}",
            f"[b]Title:[/b]         {row.get('ContactTitle') or ''}",
            f"[b]Address:[/b]       {row.get('Address') or ''}",
            f"[b]City:[/b]          {row.get('City') or ''}",
            f"[b]Region:[/b]        {row.get('Region') or ''}",
            f"[b]Postal Code:[/b]   {row.get('PostalCode') or ''}",
            f"[b]Country:[/b]       {row.get('Country') or ''}",
            f"[b]Phone:[/b]         {row.get('Phone') or ''}",
            f"[b]Fax:[/b]           {row.get('Fax') or ''}",
        ]
        self.query_one("#detail-content", Static).update("\n".join(lines))

    @on(Button.Pressed, "#btn-edit")
    def on_edit(self) -> None:
        def after(saved):
            if saved:
                self._changed = True
                self._load()
        self.app.push_screen(CustomerFormModal(pk=self.pk), callback=after)

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        row = cdata.get_by_pk(self.pk)
        name = row.get("CompanyName", self.pk) if row else self.pk

        def after_confirm(confirmed):
            if confirmed:
                try:
                    cdata.delete(self.pk)
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


class CustomersPanel(Widget):
    BINDINGS = [
        ("n", "new_record",               "New Customer"),
        ("f", "focus_search",             "Search"),
        ("+", "new_order_for_customer",   "New Order"),
        ("x", "export_csv",               "Export CSV"),
    ]

    _selected_pk: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Input(placeholder="Search customers...", id="search-box")
            yield DataTable(id="tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("+ New",   id="btn-new",    variant="success")
                yield Button("Open",    id="btn-open")
                yield Button("Delete",  id="btn-delete", variant="error")
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        for label, width in [
            ("ID", 6), ("Company", 25), ("Contact", 18),
            ("City", 14), ("Country", 10), ("Phone", 16),
        ]:
            tbl.add_column(label, width=width)
        self.refresh_data()

    def refresh_data(self, term: str = "") -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        rows = cdata.search(term) if term else cdata.fetch_all()
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

    def _open_detail(self, pk: str) -> None:
        def after(changed):
            if changed:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(CustomerDetailModal(pk=pk), callback=after)

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-open")
    def on_btn_open(self) -> None:
        if self._selected_pk:
            self._open_detail(self._selected_pk)
        else:
            self.notify("Select a customer first.", severity="warning")

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        if not self._selected_pk:
            self.notify("Select a customer first.", severity="warning")
            return
        row = cdata.get_by_pk(self._selected_pk)
        name = row.get("CompanyName", self._selected_pk) if row else self._selected_pk

        def after_confirm(confirmed):
            if confirmed:
                try:
                    cdata.delete(self._selected_pk)
                    self._selected_pk = None
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify("Customer deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")

        self.app.push_screen(ConfirmDeleteModal(name), callback=after_confirm)

    def action_new_record(self) -> None:
        def after(saved):
            if saved:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(CustomerFormModal(pk=None), callback=after)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()

    def action_export_csv(self) -> None:
        import csv, os
        from datetime import datetime
        term = self.query_one("#search-box", Input).value
        rows = cdata.search(term) if term else cdata.fetch_all()
        headers = ["ID", "Company", "Contact", "City", "Country", "Phone"]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.expanduser(f"~/Downloads/northwind_customers_{ts}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([str(c) if c is not None else "" for c in row])
        self.notify(f"Exported {len(rows)} rows → {path}", severity="information")

    def action_new_order_for_customer(self) -> None:
        if not self._selected_pk:
            self.notify("Select a customer first.", severity="warning")
            return
        from screens.orders import OrderFormModal, OrderDetailModal
        from textual.widgets import ContentSwitcher

        def after_form(order_id):
            if order_id:
                def after_detail(result):
                    try:
                        self.app.query_one(ContentSwitcher).current = "orders"
                        self.app.query_one("#orders").refresh_data()
                    except Exception:
                        pass
                self.app.push_screen(OrderDetailModal(order_id), callback=after_detail)

        self.app.push_screen(
            OrderFormModal(customer_id=self._selected_pk), callback=after_form
        )
