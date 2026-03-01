"""screens/export_helpers.py — Centralised CSV export logic."""
import csv
import os
from datetime import datetime


def default_csv_path(entity: str) -> str:
    """Return ~/Downloads/northwind_{entity}_{timestamp}.csv"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.expanduser(f"~/Downloads/northwind_{entity}_{ts}.csv")


def write_csv(path: str, headers: list[str], rows: list) -> int:
    """Write CSV file. Returns row count."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([str(c) if c is not None else "" for c in row])
    return len(rows)


def export_csv_with_selector(widget, entity: str, headers: list[str], rows: list) -> None:
    """Open FileSelectModal(mode='save'), then write CSV to chosen path."""
    from screens.modals import FileSelectModal

    suggested = f"northwind_{entity}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    def after(path):
        if path:
            try:
                count = write_csv(path, headers, rows)
                widget.notify(f"Exported {count} rows → {path}", severity="information")
            except Exception as e:
                widget.notify(f"Export error: {e}", severity="error")

    widget.app.push_screen(
        FileSelectModal(
            title=f"Export {entity.replace('_', ' ').title()} CSV",
            mode="save",
            default_path="~/Downloads",
            suggested_name=suggested,
            file_filter=".csv",
        ),
        callback=after,
    )
