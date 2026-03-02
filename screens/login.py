"""screens/login.py — Full-screen login gate (PIN-based).

Educational patterns:
- ModalScreen pushed before the main UI renders (login gate pattern)
- dismiss(result) passes data back to the caller via callback
- ESC is intentionally swallowed so the user cannot skip login
"""
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label
from textual import on
from textual.events import Key

import data.users as users


class LoginScreen(ModalScreen):
    """Full-screen login modal — not dismissable with ESC."""

    # Override default bindings so ESC does nothing
    BINDINGS = []

    def compose(self) -> ComposeResult:
        with Vertical(classes="login-box"):
            yield Label("Northwind Traders v2.13", classes="login-title")
            yield Label("Please log in", classes="login-subtitle")
            yield Label("Username")
            yield Input(placeholder="Username", id="f-username")
            yield Label("PIN")
            yield Input(placeholder="PIN (4 digits)", id="f-pin", password=True, max_length=4)
            yield Label("", id="login-error", classes="login-error")
            yield Button("Login", id="btn-login", variant="primary")

    def on_key(self, event: Key) -> None:
        """Swallow ESC so the user cannot dismiss the login screen."""
        if event.key == "escape":
            event.prevent_default()
            event.stop()

    @on(Input.Submitted)
    def on_input_submitted(self) -> None:
        self._attempt_login()

    @on(Button.Pressed, "#btn-login")
    def on_login_pressed(self) -> None:
        self._attempt_login()

    def _attempt_login(self) -> None:
        username = self.query_one("#f-username", Input).value.strip()
        pin = self.query_one("#f-pin", Input).value.strip()
        user = users.authenticate(username, pin)
        if user:
            self.dismiss(user)
        else:
            self.query_one("#login-error", Label).update("Invalid username or PIN.")
