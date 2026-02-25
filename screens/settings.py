"""screens/settings.py — App settings panel (currency symbol & name).

Educational patterns:
- on_mount() to pre-populate inputs from the DB
- INSERT OR REPLACE upsert via the settings data layer
- notify() for lightweight user feedback without a modal
"""
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label
from textual import on

import data.settings as app_settings


class SettingsPanel(Widget):
    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Label("Settings", classes="panel-title")
            with Vertical(classes="settings-section"):
                yield Label("Currency", classes="settings-label")
                yield Label("Symbol (e.g. $, £, €, zł)")
                yield Input(placeholder="$", id="f-currency-symbol")
                yield Label("Name (e.g. USD, GBP, PLN)")
                yield Input(placeholder="USD", id="f-currency-name")
            yield Button("Save Settings", id="btn-save", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#f-currency-symbol", Input).value = app_settings.get_setting(
            "currency_symbol", "$"
        )
        self.query_one("#f-currency-name", Input).value = app_settings.get_setting(
            "currency_name", "USD"
        )

    @on(Button.Pressed, "#btn-save")
    def do_save(self) -> None:
        symbol = self.query_one("#f-currency-symbol", Input).value.strip()
        name   = self.query_one("#f-currency-name",   Input).value.strip()
        if symbol:
            app_settings.set_setting("currency_symbol", symbol)
        if name:
            app_settings.set_setting("currency_name", name)
        self.notify("Settings saved.", severity="information")
