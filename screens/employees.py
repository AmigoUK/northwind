"""screens/employees.py — Employees panel, detail, form, and org chart modals."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static, Tree
from textual import on

import data.employees as edata
from screens.modals import ConfirmDeleteModal, PickerModal


class OrgChartModal(ModalScreen):
    """Display employee hierarchy using Textual Tree widget."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="org-dialog"):
            yield Label("Employee Org Chart", classes="modal-title")
            yield Tree("Northwind Traders", id="org-tree")
            with Horizontal(classes="modal-buttons"):
                yield Button("Close", id="btn-close", variant="primary")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        tree = self.query_one(Tree)
        tree.root.expand()
        employees = edata.fetch_with_hierarchy()

        # Build children map
        children: dict = {}
        for emp in employees:
            mgr = emp["ReportsTo"]
            if mgr not in children:
                children[mgr] = []
            children[mgr].append(emp)

        def add_nodes(parent_node, emp_id):
            for emp in children.get(emp_id, []):
                label = f"{emp['FirstName']} {emp['LastName']} ({emp['Title'] or 'N/A'})"
                child = parent_node.add(label)
                add_nodes(child, emp["EmployeeID"])

        for emp in children.get(None, []):
            label = f"{emp['FirstName']} {emp['LastName']} ({emp['Title'] or 'N/A'})"
            top_node = tree.root.add(label)
            top_node.expand()
            add_nodes(top_node, emp["EmployeeID"])

    @on(Button.Pressed, "#btn-close")
    def on_close(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class EmployeeFormModal(ModalScreen):
    def __init__(self, pk=None) -> None:
        super().__init__()
        self.pk = pk
        self._reports_to = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(
                "Add Employee" if not self.pk else f"Edit Employee #{self.pk}",
                classes="modal-title",
            )
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Last Name *:")
                    yield Input(id="f-lastname", placeholder="Last Name")
                with Vertical(classes="form-field"):
                    yield Label("First Name *:")
                    yield Input(id="f-firstname", placeholder="First Name")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Title:")
                    yield Input(id="f-title", placeholder="Title")
                with Vertical(classes="form-field"):
                    yield Label("Title of Courtesy:")
                    yield Input(id="f-toc", placeholder="Mr./Ms./Dr.")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Birth Date (YYYY-MM-DD):")
                    yield Input(id="f-birth", placeholder="1970-01-01")
                with Vertical(classes="form-field"):
                    yield Label("Hire Date (YYYY-MM-DD):")
                    yield Input(id="f-hire", placeholder="2000-01-01")
            yield Label("Address:")
            yield Input(id="f-address", placeholder="Address")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("City:")
                    yield Input(id="f-city", placeholder="City")
                with Vertical(classes="form-field"):
                    yield Label("Region:")
                    yield Input(id="f-region", placeholder="Region")
                with Vertical(classes="form-field"):
                    yield Label("Postal Code:")
                    yield Input(id="f-postal", placeholder="Postal Code")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Country:")
                    yield Input(id="f-country", placeholder="Country")
                with Vertical(classes="form-field"):
                    yield Label("Home Phone:")
                    yield Input(id="f-phone", placeholder="Phone")
                with Vertical(classes="form-field"):
                    yield Label("Extension:")
                    yield Input(id="f-ext", placeholder="Extension")
            yield Label("Notes:")
            yield Input(id="f-notes", placeholder="Notes")
            yield Label("Reports To:")
            with Horizontal():
                yield Label("(none)", id="lbl-manager")
                yield Button("Pick Manager ▼", id="btn-pick-mgr")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        if self.pk:
            row = edata.get_by_pk(self.pk)
            if row:
                self.query_one("#f-lastname",  Input).value = row.get("LastName")        or ""
                self.query_one("#f-firstname", Input).value = row.get("FirstName")       or ""
                self.query_one("#f-title",     Input).value = row.get("Title")           or ""
                self.query_one("#f-toc",       Input).value = row.get("TitleOfCourtesy") or ""
                self.query_one("#f-birth",     Input).value = row.get("BirthDate")       or ""
                self.query_one("#f-hire",      Input).value = row.get("HireDate")        or ""
                self.query_one("#f-address",   Input).value = row.get("Address")         or ""
                self.query_one("#f-city",      Input).value = row.get("City")            or ""
                self.query_one("#f-region",    Input).value = row.get("Region")          or ""
                self.query_one("#f-postal",    Input).value = row.get("PostalCode")      or ""
                self.query_one("#f-country",   Input).value = row.get("Country")         or ""
                self.query_one("#f-phone",     Input).value = row.get("HomePhone")       or ""
                self.query_one("#f-ext",       Input).value = row.get("Extension")       or ""
                self.query_one("#f-notes",     Input).value = row.get("Notes")           or ""
                self._reports_to = row.get("ReportsTo")
                if self._reports_to:
                    mgr = edata.get_by_pk(self._reports_to)
                    if mgr:
                        name = f"{mgr['FirstName']} {mgr['LastName']}"
                        self.query_one("#lbl-manager", Label).update(name)

    @on(Button.Pressed, "#btn-pick-mgr")
    def on_pick_manager(self) -> None:
        rows = edata.fetch_for_picker()
        def after(pk):
            if pk:
                self._reports_to = int(pk)
                mgr = edata.get_by_pk(int(pk))
                if mgr:
                    self.query_one("#lbl-manager", Label).update(
                        f"{mgr['FirstName']} {mgr['LastName']}"
                    )
        self.app.push_screen(
            PickerModal("Select Manager", [("ID", 4), ("Name", 26), ("Title", 28)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        from datetime import datetime
        last  = self.query_one("#f-lastname",  Input).value.strip()
        first = self.query_one("#f-firstname", Input).value.strip()
        if not last or not first:
            self.notify("Last Name and First Name are required.", severity="error")
            return

        # Validate dates
        birth = self.query_one("#f-birth", Input).value.strip()
        hire  = self.query_one("#f-hire",  Input).value.strip()
        for label, val in [("Birth Date", birth), ("Hire Date", hire)]:
            if val:
                try:
                    datetime.strptime(val, "%Y-%m-%d")
                except ValueError:
                    self.notify(f"{label} must be YYYY-MM-DD.", severity="error")
                    return

        data = {
            "LastName":        last,
            "FirstName":       first,
            "Title":           self.query_one("#f-title",   Input).value.strip(),
            "TitleOfCourtesy": self.query_one("#f-toc",     Input).value.strip(),
            "BirthDate":       birth or None,
            "HireDate":        hire  or None,
            "Address":         self.query_one("#f-address", Input).value.strip(),
            "City":            self.query_one("#f-city",    Input).value.strip(),
            "Region":          self.query_one("#f-region",  Input).value.strip(),
            "PostalCode":      self.query_one("#f-postal",  Input).value.strip(),
            "Country":         self.query_one("#f-country", Input).value.strip(),
            "HomePhone":       self.query_one("#f-phone",   Input).value.strip(),
            "Extension":       self.query_one("#f-ext",     Input).value.strip(),
            "Notes":           self.query_one("#f-notes",   Input).value.strip(),
            "ReportsTo":       self._reports_to,
        }
        try:
            if self.pk is None:
                edata.insert(data)
                self.notify(f"Employee '{first} {last}' added.", severity="information")
            else:
                edata.update(self.pk, data)
                self.notify("Employee updated.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class EmployeeDetailModal(ModalScreen):
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
        row = edata.get_by_pk(self.pk)
        if not row:
            self.dismiss(self._changed)
            return
        name = f"{row.get('TitleOfCourtesy', '')} {row['FirstName']} {row['LastName']}".strip()
        self.query_one("#detail-title", Label).update(f"Employee #{self.pk}: {name}")

        # Resolve manager
        manager_str = "(none)"
        if row.get("ReportsTo"):
            mgr = edata.get_by_pk(row["ReportsTo"])
            if mgr:
                manager_str = f"#{row['ReportsTo']} {mgr['FirstName']} {mgr['LastName']}"

        lines = [
            f"[b]ID:[/b]            {row['EmployeeID']}",
            f"[b]Name:[/b]          {name}",
            f"[b]Title:[/b]         {row.get('Title') or ''}",
            f"[b]Birth Date:[/b]    {row.get('BirthDate') or ''}",
            f"[b]Hire Date:[/b]     {row.get('HireDate') or ''}",
            f"[b]Address:[/b]       {row.get('Address') or ''}",
            f"[b]City:[/b]          {row.get('City') or ''}",
            f"[b]Region:[/b]        {row.get('Region') or ''}",
            f"[b]Postal Code:[/b]   {row.get('PostalCode') or ''}",
            f"[b]Country:[/b]       {row.get('Country') or ''}",
            f"[b]Home Phone:[/b]    {row.get('HomePhone') or ''}",
            f"[b]Extension:[/b]     {row.get('Extension') or ''}",
            f"[b]Reports To:[/b]    {manager_str}",
            f"[b]Notes:[/b]         {(row.get('Notes') or '')[:80]}",
        ]
        self.query_one("#detail-content", Static).update("\n".join(lines))

    @on(Button.Pressed, "#btn-edit")
    def on_edit(self) -> None:
        def after(saved):
            if saved:
                self._changed = True
                self._load()
        self.app.push_screen(EmployeeFormModal(pk=self.pk), callback=after)

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        row = edata.get_by_pk(self.pk)
        name = f"{row['FirstName']} {row['LastName']}" if row else str(self.pk)

        def after_confirm(confirmed):
            if confirmed:
                try:
                    edata.delete(self.pk)
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


class EmployeesPanel(Widget):
    BINDINGS = [
        ("n", "new_record",   "New Employee"),
        ("f", "focus_search", "Search"),
        ("o", "org_chart",    "Org Chart"),
    ]

    _selected_pk = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Input(placeholder="Search employees...", id="search-box")
            yield DataTable(id="tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("+ New",     id="btn-new",    variant="success")
                yield Button("Open",      id="btn-open")
                yield Button("Delete",    id="btn-delete", variant="error")
                yield Button("Org Chart", id="btn-org")
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        for label, width in [
            ("ID", 4), ("Name", 22), ("Title", 25),
            ("City", 12), ("Manager", 22),
        ]:
            tbl.add_column(label, width=width)
        self.refresh_data()

    def refresh_data(self, term: str = "") -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        rows = edata.search(term) if term else edata.fetch_all()
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
        self.app.push_screen(EmployeeDetailModal(pk=int(pk)), callback=after)

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-open")
    def on_btn_open(self) -> None:
        if self._selected_pk:
            self._open_detail(self._selected_pk)
        else:
            self.notify("Select an employee first.", severity="warning")

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        if not self._selected_pk:
            self.notify("Select an employee first.", severity="warning")
            return
        row = edata.get_by_pk(int(self._selected_pk))
        name = f"{row['FirstName']} {row['LastName']}" if row else str(self._selected_pk)

        def after_confirm(confirmed):
            if confirmed:
                try:
                    edata.delete(int(self._selected_pk))
                    self._selected_pk = None
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify("Employee deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")

        self.app.push_screen(ConfirmDeleteModal(name), callback=after_confirm)

    @on(Button.Pressed, "#btn-org")
    def on_btn_org(self) -> None:
        self.action_org_chart()

    def action_new_record(self) -> None:
        def after(saved):
            if saved:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(EmployeeFormModal(pk=None), callback=after)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()

    def action_export_csv(self) -> None:
        from screens.export_helpers import export_csv_with_selector
        term = self.query_one("#search-box", Input).value
        rows = edata.search(term) if term else edata.fetch_all()
        export_csv_with_selector(self, "employees", ["ID", "Name", "Title", "City", "Manager"], rows)

    def action_org_chart(self) -> None:
        self.app.push_screen(OrgChartModal())
