"""screens/business.py — Business Details panel.

Stores company identity, contact, tax/legal info, logo path and document
defaults in the existing AppSettings key-value store.  No new DB table.
"""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Switch, TabbedContent, TabPane
from textual import on

import data.settings as app_settings


class BusinessDetailsPanel(Widget):
    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Label("Business Details", classes="panel-title")

            with TabbedContent():

                # Tab 1 — Company
                with TabPane("Company", id="tab-company"):
                    with Vertical(classes="settings-section"):
                        yield Label("Company & Contact", classes="settings-label")
                        yield Label("Company Name")
                        yield Input(placeholder="Acme Ltd.", id="f-co-name")
                        with Horizontal(classes="form-row"):
                            with Vertical(classes="form-field"):
                                yield Label("Address")
                                yield Input(placeholder="123 Main St", id="f-co-address")
                            with Vertical(classes="form-field"):
                                yield Label("Country")
                                yield Input(placeholder="Poland", id="f-co-country")
                        with Horizontal(classes="form-row"):
                            with Vertical(classes="form-field"):
                                yield Label("City")
                                yield Input(placeholder="Warsaw", id="f-co-city")
                            with Vertical(classes="form-field"):
                                yield Label("Postal Code")
                                yield Input(placeholder="00-001", id="f-co-postal")
                        with Horizontal(classes="form-row"):
                            with Vertical(classes="form-field"):
                                yield Label("Phone")
                                yield Input(placeholder="+48 22 000 0000", id="f-co-phone")
                            with Vertical(classes="form-field"):
                                yield Label("Email")
                                yield Input(placeholder="info@example.com", id="f-co-email")
                        with Horizontal(classes="form-row"):
                            with Vertical(classes="form-field"):
                                yield Label("Website")
                                yield Input(placeholder="https://example.com", id="f-co-website")
                            with Vertical(classes="form-field"):
                                yield Label("Logo path (for PDFs)")
                                yield Input(placeholder="/path/to/logo.png", id="f-co-logo-path")

                # Tab 2 — Tax & Legal
                with TabPane("Tax & Legal", id="tab-tax"):
                    with Vertical(classes="settings-section"):
                        yield Label("Tax & Legal", classes="settings-label")
                        with Horizontal(classes="form-row"):
                            with Vertical(classes="form-field"):
                                yield Label("VAT Number")
                                yield Input(placeholder="PL1234567890", id="f-co-vat")
                            with Vertical(classes="form-field"):
                                yield Label("Tax ID / NIP")
                                yield Input(placeholder="1234567890", id="f-co-tax-id")
                        yield Label("Bank Account")
                        yield Input(placeholder="PL61 1090 1014 0000 0712 1981 2874", id="f-co-bank-account")

                # Tab 3 — Document Defaults
                with TabPane("Documents", id="tab-docs"):
                    with Vertical(classes="settings-section"):
                        yield Label("Document Defaults", classes="settings-label")
                        yield Label("Footer note (appears on all documents)")
                        yield Input(placeholder="Thank you for your business.", id="f-doc-footer")
                        yield Label("Document colour theme")
                        yield Select(
                            [
                                ("Default", "default"),
                                ("Blue", "blue"),
                                ("Green", "green"),
                                ("Monochrome", "monochrome"),
                            ],
                            id="f-doc-theme",
                            allow_blank=False,
                            value="default",
                        )
                        with Horizontal(classes="form-row"):
                            with Vertical(classes="form-field"):
                                yield Label("DN title")
                                yield Input(placeholder="Delivery Note", id="f-doc-title-dn")
                            with Vertical(classes="form-field"):
                                yield Label("INV title")
                                yield Input(placeholder="Invoice", id="f-doc-title-inv")
                            with Vertical(classes="form-field"):
                                yield Label("GR title")
                                yield Input(placeholder="Goods Receipt", id="f-doc-title-gr")
                        with Horizontal(classes="setting-row"):
                            yield Label("Show unit prices on DN delivery notes")
                            yield Switch(id="sw-dn-prices", value=True)

            yield Button("Save", id="btn-save", variant="primary")

    def on_mount(self) -> None:
        gs = app_settings.get_setting
        self.query_one("#f-co-name",         Input).value = gs("co_name",         "")
        self.query_one("#f-co-address",      Input).value = gs("co_address",      "")
        self.query_one("#f-co-city",         Input).value = gs("co_city",         "")
        self.query_one("#f-co-postal",       Input).value = gs("co_postal",       "")
        self.query_one("#f-co-country",      Input).value = gs("co_country",      "")
        self.query_one("#f-co-logo-path",    Input).value = gs("co_logo_path",    "")
        self.query_one("#f-co-phone",        Input).value = gs("co_phone",        "")
        self.query_one("#f-co-email",        Input).value = gs("co_email",        "")
        self.query_one("#f-co-website",      Input).value = gs("co_website",      "")
        self.query_one("#f-co-vat",          Input).value = gs("co_vat",          "")
        self.query_one("#f-co-tax-id",       Input).value = gs("co_tax_id",       "")
        self.query_one("#f-co-bank-account", Input).value = gs("co_bank_account", "")
        self.query_one("#f-doc-footer",      Input).value = gs("doc_footer",      "")
        self.query_one("#f-doc-theme",  Select).value     = gs("doc_theme",       "default")
        self.query_one("#f-doc-title-dn",    Input).value = gs("doc_title_dn",    "Delivery Note")
        self.query_one("#f-doc-title-inv",   Input).value = gs("doc_title_inv",   "Invoice")
        self.query_one("#f-doc-title-gr",    Input).value = gs("doc_title_gr",    "Goods Receipt")
        self.query_one("#sw-dn-prices", Switch).value = (
            gs("doc_dn_show_prices", "true").lower() == "true"
        )

    @on(Button.Pressed, "#btn-save")
    def do_save(self) -> None:
        ss = app_settings.set_setting
        ss("co_name",         self.query_one("#f-co-name",         Input).value.strip())
        ss("co_address",      self.query_one("#f-co-address",      Input).value.strip())
        ss("co_city",         self.query_one("#f-co-city",         Input).value.strip())
        ss("co_postal",       self.query_one("#f-co-postal",       Input).value.strip())
        ss("co_country",      self.query_one("#f-co-country",      Input).value.strip())
        ss("co_logo_path",    self.query_one("#f-co-logo-path",    Input).value.strip())
        ss("co_phone",        self.query_one("#f-co-phone",        Input).value.strip())
        ss("co_email",        self.query_one("#f-co-email",        Input).value.strip())
        ss("co_website",      self.query_one("#f-co-website",      Input).value.strip())
        ss("co_vat",          self.query_one("#f-co-vat",          Input).value.strip())
        ss("co_tax_id",       self.query_one("#f-co-tax-id",       Input).value.strip())
        ss("co_bank_account", self.query_one("#f-co-bank-account", Input).value.strip())
        ss("doc_footer",      self.query_one("#f-doc-footer",      Input).value.strip())
        theme_val = self.query_one("#f-doc-theme", Select).value
        if theme_val and theme_val != Select.BLANK:
            ss("doc_theme", str(theme_val))
        ss("doc_title_dn",    self.query_one("#f-doc-title-dn",    Input).value.strip())
        ss("doc_title_inv",   self.query_one("#f-doc-title-inv",   Input).value.strip())
        ss("doc_title_gr",    self.query_one("#f-doc-title-gr",    Input).value.strip())
        dn_prices = self.query_one("#sw-dn-prices", Switch).value
        ss("doc_dn_show_prices", "true" if dn_prices else "false")
        self.notify("Business details saved.", severity="information")
