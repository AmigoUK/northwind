"""screens/users.py — User management panel (admin-only).

Educational patterns:
- ModalScreen for add/edit forms (same pattern as other panels)
- Role-based guard: cannot delete yourself
- Select widget for fixed-choice fields
- Conditional PIN update (leave blank to keep existing hash)
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select
from textual import on
from textual.events import Key

import data.users as users


class UserFormModal(ModalScreen):
    """Add / Edit user form."""

    def __init__(self, user: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self._user = user  # None → new user

    def compose(self) -> ComposeResult:
        title = "Edit User" if self._user else "New User"
        with Vertical(classes="modal-dialog"):
            yield Label(title, classes="modal-title")
            yield Label("Username")
            yield Input(
                value=self._user["username"] if self._user else "",
                placeholder="username",
                id="f-username",
            )
            yield Label("Display Name")
            yield Input(
                value=self._user["display_name"] if self._user else "",
                placeholder="Display Name",
                id="f-display-name",
            )
            yield Label("PIN (leave blank to keep existing)" if self._user else "PIN (4 digits)")
            yield Input(placeholder="••••", id="f-pin", password=True, max_length=4)
            yield Label("Role")
            yield Select(
                [("User", "user"), ("Admin", "admin")],
                value=self._user["role"] if self._user else "user",
                id="f-role",
            )
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            self.dismiss(None)

    @on(Button.Pressed, "#btn-cancel")
    def do_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#btn-save")
    def do_save(self) -> None:
        username     = self.query_one("#f-username",     Input).value.strip()
        display_name = self.query_one("#f-display-name", Input).value.strip()
        pin          = self.query_one("#f-pin",          Input).value.strip()
        role_val     = self.query_one("#f-role",         Select).value

        # Select.BLANK guard
        role = str(role_val) if role_val is not Select.BLANK else "user"

        if not username or not display_name:
            self.notify("Username and Display Name are required.", severity="error")
            return
        if not self._user and not pin:
            self.notify("PIN is required for new users.", severity="error")
            return

        self.dismiss({"username": username, "display_name": display_name, "pin": pin, "role": role})


class UsersPanel(Widget):
    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Label("User Management", classes="panel-title")
            with Horizontal(classes="toolbar"):
                yield Button("+ New",  id="btn-new",    variant="primary")
                yield Button("Edit",   id="btn-edit")
                yield Button("Delete", id="btn-delete", variant="error")
            yield DataTable(id="users-tbl", cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        tbl = self.query_one("#users-tbl", DataTable)
        for label, width in [
            ("ID", 6), ("Username", 20), ("Display Name", 25), ("Role", 10), ("Created", 22),
        ]:
            tbl.add_column(label, width=width)
        self._load()

    def _load(self) -> None:
        tbl = self.query_one("#users-tbl", DataTable)
        tbl.clear()
        for row in users.fetch_all():
            created = row["created_at"][:19] if row["created_at"] else ""
            tbl.add_row(
                str(row["user_id"]),
                row["username"],
                row["display_name"],
                row["role"],
                created,
                key=str(row["user_id"]),
            )

    def _selected_pk(self) -> int | None:
        tbl = self.query_one("#users-tbl", DataTable)
        if tbl.row_count == 0:
            return None
        try:
            row = tbl.get_row_at(tbl.cursor_row)
            return int(row[0])
        except Exception:
            return None

    @on(Button.Pressed, "#btn-new")
    def do_new(self) -> None:
        self.app.push_screen(UserFormModal(), self._after_new)

    @on(Button.Pressed, "#btn-edit")
    def do_edit(self) -> None:
        pk = self._selected_pk()
        if pk is None:
            self.notify("Select a user to edit.", severity="warning")
            return
        user = users.get_by_pk(pk)
        if user:
            self.app.push_screen(
                UserFormModal(user=user),
                lambda data: self._after_edit(pk, data),
            )

    @on(Button.Pressed, "#btn-delete")
    def do_delete(self) -> None:
        pk = self._selected_pk()
        if pk is None:
            self.notify("Select a user to delete.", severity="warning")
            return
        current_user = getattr(self.app, "_current_user", None)
        if current_user and current_user.get("user_id") == pk:
            self.notify("Cannot delete yourself.", severity="error")
            return
        users.delete(pk)
        self._load()
        self.notify("User deleted.", severity="information")

    def _after_new(self, data: dict | None) -> None:
        if data:
            try:
                users.insert(data)
                self._load()
                self.notify("User created.", severity="information")
            except Exception as e:
                self.notify(f"Error: {e}", severity="error")

    def _after_edit(self, pk: int, data: dict | None) -> None:
        if data:
            try:
                users.update(pk, data)
                self._load()
                self.notify("User updated.", severity="information")
            except Exception as e:
                self.notify(f"Error: {e}", severity="error")
