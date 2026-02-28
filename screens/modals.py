"""screens/modals.py — Shared modal dialogs: ConfirmDeleteModal, PickerModal."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label
from textual import on


class ConfirmActionModal(ModalScreen[bool]):
    """Generic confirmation dialog with custom title and button label."""

    def __init__(self, title: str, message: str = "", confirm_label: str = "Confirm") -> None:
        super().__init__()
        self._title = title
        self._message = message
        self._confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        with Vertical(classes="confirm-dialog"):
            yield Label(self._title, classes="modal-title")
            if self._message:
                yield Label(self._message, classes="modal-subtitle")
            with Horizontal(classes="modal-buttons"):
                yield Button(self._confirm_label, id="btn-yes", variant="primary")
                yield Button("Cancel", id="btn-no")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#btn-no").focus()

    def on_key(self, event) -> None:
        if event.key == "y":
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            self.dismiss(False)

    @on(Button.Pressed, "#btn-yes")
    def on_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-no")
    def on_no(self) -> None:
        self.dismiss(False)


class ConfirmDeleteModal(ModalScreen[bool]):
    """Ask the user to confirm deletion. Returns True if confirmed."""

    def __init__(self, name: str, details: str = "") -> None:
        super().__init__()
        self._name = name
        self._details = details

    def compose(self) -> ComposeResult:
        with Vertical(classes="confirm-dialog"):
            yield Label(f"Delete '{self._name}'?", classes="modal-title")
            if self._details:
                yield Label(self._details, classes="modal-subtitle")
            yield Label("This action cannot be undone.", classes="modal-subtitle")
            with Horizontal(classes="modal-buttons"):
                yield Button("Delete", id="btn-yes", variant="error")
                yield Button("Cancel", id="btn-no", variant="primary")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#btn-no").focus()

    def on_key(self, event) -> None:
        if event.key == "y":
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            self.dismiss(False)

    @on(Button.Pressed, "#btn-yes")
    def on_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-no")
    def on_no(self) -> None:
        self.dismiss(False)


class QuitConfirmModal(ModalScreen[bool]):
    """Ask the user to confirm quitting the app. Returns True if confirmed."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="confirm-dialog"):
            yield Label("Quit Northwind Traders?", classes="modal-title")
            yield Label("Press Y to quit or N / ESC to cancel.", classes="modal-subtitle")
            with Horizontal(classes="modal-buttons"):
                yield Button("Quit", id="btn-yes", variant="error")
                yield Button("Cancel", id="btn-no", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#btn-no").focus()  # safe default: Cancel focused

    def on_key(self, event) -> None:
        if event.key == "y":
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            self.dismiss(False)

    @on(Button.Pressed, "#btn-yes")
    def on_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-no")
    def on_no(self) -> None:
        self.dismiss(False)


class CancellationReasonModal(ModalScreen):
    """Ask for a mandatory cancellation reason. Returns reason string or None."""

    def __init__(self, title: str, warning: str = "") -> None:
        super().__init__()
        self._title = title
        self._warning = warning

    def compose(self) -> ComposeResult:
        with Vertical(classes="confirm-dialog"):
            yield Label(self._title, classes="modal-title")
            if self._warning:
                yield Label(self._warning, classes="modal-subtitle")
            yield Label("Reason (required):")
            yield Input(placeholder="Cancellation reason...", id="f-reason")
            with Horizontal(classes="modal-buttons"):
                yield Button("Confirm Cancel", id="btn-yes", variant="warning")
                yield Button("Back", id="btn-no", variant="primary")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#f-reason", Input).focus()

    @on(Button.Pressed, "#btn-yes")
    def on_yes(self) -> None:
        reason = self.query_one("#f-reason", Input).value.strip()
        if not reason:
            self.notify("Reason is required.", severity="error")
            return
        self.dismiss(reason)

    @on(Button.Pressed, "#btn-no")
    def on_no(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class PickerModal(ModalScreen):
    """Reusable record picker. Returns the selected pk string or None."""

    def __init__(
        self,
        title: str,
        headers: list[tuple[str, int]],
        rows: list[list],
        pk_col: int = 0,
    ) -> None:
        super().__init__()
        self._title = title
        self._headers = headers
        self._all_rows = rows
        self._pk_col = pk_col

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(self._title, classes="modal-title")
            yield Input(placeholder="Filter...", id="picker-filter")
            yield DataTable(id="picker-tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="modal-buttons"):
                yield Button("Select", id="btn-select", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        tbl = self.query_one("#picker-tbl", DataTable)
        for label, width in self._headers:
            tbl.add_column(label, width=width)
        self._populate(self._all_rows)

    def _populate(self, rows: list) -> None:
        tbl = self.query_one("#picker-tbl", DataTable)
        tbl.clear()
        for row in rows:
            tbl.add_row(*[str(c) if c is not None else "" for c in row],
                        key=str(row[self._pk_col]))

    @on(Input.Changed, "#picker-filter")
    def on_filter(self, event: Input.Changed) -> None:
        term = event.value.lower()
        if term:
            filtered = [r for r in self._all_rows
                        if any(term in str(c).lower() for c in r)]
        else:
            filtered = self._all_rows
        self._populate(filtered)

    @on(DataTable.RowSelected, "#picker-tbl")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key:
            self.dismiss(event.row_key.value)

    @on(Button.Pressed, "#btn-select")
    def on_select(self) -> None:
        tbl = self.query_one("#picker-tbl", DataTable)
        if tbl.row_count == 0:
            self.dismiss(None)
            return
        try:
            pk = tbl.coordinate_to_cell_key(tbl.cursor_coordinate).row_key.value
            self.dismiss(pk)
        except Exception:
            self.dismiss(None)

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
