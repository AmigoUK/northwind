"""
app.py — Northwind Traders v2.0
Textual TUI entry point.
"""
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import (
    ContentSwitcher,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
)
from textual import on

from db import init_db
from screens.dashboard  import DashboardPanel
from screens.customers  import CustomersPanel
from screens.orders     import OrdersPanel
from screens.products   import ProductsPanel
from screens.employees  import EmployeesPanel
from screens.suppliers  import SuppliersPanel
from screens.categories import CategoriesPanel
from screens.shippers   import ShippersPanel
from screens.regions    import RegionsPanel
from screens.reports    import ReportsPanel


_SECTIONS = [
    ("dashboard",  "Dashboard"),
    ("customers",  "Customers"),
    ("orders",     "Orders"),
    ("products",   "Products"),
    ("employees",  "Employees"),
    ("suppliers",  "Suppliers"),
    ("categories", "Categories"),
    ("shippers",   "Shippers"),
    ("regions",    "Regions"),
    ("reports",    "Reports"),
]


class SidebarNav(Widget):
    """Left navigation sidebar."""

    def compose(self) -> ComposeResult:
        yield Label("Northwind", id="sidebar-title")
        with ListView(id="nav-list"):
            for key, label in _SECTIONS:
                yield ListItem(Label(label), id=f"nav-{key}")

    @on(ListView.Selected, "#nav-list")
    def on_nav_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        if item_id and item_id.startswith("nav-"):
            section = item_id[4:]
            self.app.switch_section(section)


class NorthwindApp(App):
    TITLE = "Northwind Traders v2.0"
    CSS_PATH = "northwind.tcss"

    BINDINGS = [
        Binding("q",      "quit",    "Quit"),
        Binding("n",      "new",     "New",    show=True),
        Binding("f",      "search",  "Search", show=True),
        Binding("escape", "escape",  "Back",   show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield SidebarNav(id="sidebar")
            with ContentSwitcher(id="content", initial="dashboard"):
                yield DashboardPanel(id="dashboard")
                yield CustomersPanel(id="customers")
                yield OrdersPanel(id="orders")
                yield ProductsPanel(id="products")
                yield EmployeesPanel(id="employees")
                yield SuppliersPanel(id="suppliers")
                yield CategoriesPanel(id="categories")
                yield ShippersPanel(id="shippers")
                yield RegionsPanel(id="regions")
                yield ReportsPanel(id="reports")
        yield Footer()

    def on_mount(self) -> None:
        init_db()
        # Highlight first nav item
        nav = self.query_one("#nav-list", ListView)
        nav.index = 0

    def switch_section(self, section: str) -> None:
        """Switch the active content panel."""
        self.query_one(ContentSwitcher).current = section
        # Update sidebar highlight
        for key, _ in _SECTIONS:
            item = self.query_one(f"#nav-{key}", ListItem)
            if key == section:
                item.add_class("active-nav")
            else:
                item.remove_class("active-nav")

    def action_new(self) -> None:
        """Delegate N key to the active panel."""
        current = self.query_one(ContentSwitcher).current
        try:
            panel = self.query_one(f"#{current}")
            panel.action_new_record()
        except Exception:
            pass

    def action_search(self) -> None:
        """Delegate F key to the active panel."""
        current = self.query_one(ContentSwitcher).current
        try:
            panel = self.query_one(f"#{current}")
            panel.action_focus_search()
        except Exception:
            pass

    def action_escape(self) -> None:
        """ESC is handled by individual modals; here it's a no-op at top level."""
        pass


if __name__ == "__main__":
    NorthwindApp().run()
