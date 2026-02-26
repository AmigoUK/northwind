"""pdf_export.py — PDF generation for WZ (delivery notes) and FV (invoices)."""
from __future__ import annotations

import os
from datetime import datetime

from fpdf import FPDF

from data.settings import get_setting, get_currency_symbol


def _branding() -> dict:
    """Read all co_* and doc_* keys from AppSettings once."""
    keys = [
        "co_name", "co_address", "co_city", "co_postal", "co_country",
        "co_phone", "co_email", "co_website", "co_vat", "co_tax_id",
        "co_bank_account", "co_logo_path",
        "doc_footer", "doc_theme",
        "doc_title_wz", "doc_title_fv", "doc_wz_show_prices",
    ]
    return {k: get_setting(k, "") for k in keys}


_THEMES = {
    "blue":       (31,  73, 125),
    "green":      (34, 102,  34),
    "monochrome": (  0,   0,   0),
    "default":    ( 60,  60,  60),
}


def _theme_colour(theme: str) -> tuple[int, int, int]:
    return _THEMES.get(theme, _THEMES["default"])


class _NorthwindPDF(FPDF):
    def __init__(self, footer_text: str, theme_rgb: tuple):
        super().__init__(orientation='P', unit='mm', format='A4')
        self._footer_text = footer_text
        self._theme_rgb = theme_rgb

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.set_text_color(150, 150, 150)
        if self._footer_text:
            self.cell(0, 5, self._footer_text, align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, f"Page {self.page_no()} / {{nb}}", align="R")


def _draw_header(
    pdf: _NorthwindPDF,
    b: dict,
    title: str,
    doc_number: str,
    doc_date: str,
) -> None:
    """Draw the branded header (logo, company info, doc title/number) at top of page."""
    theme = _theme_colour(b.get("doc_theme", ""))
    margin = pdf.l_margin
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    col_left_w = 90
    gap = 5
    col_right_x = margin + col_left_w + gap
    col_right_w = pdf.w - pdf.r_margin - col_right_x

    start_y = pdf.get_y()
    left_y = start_y

    # --- Left column: logo + company info ---
    logo_path = b.get("co_logo_path", "")
    if logo_path and os.path.isfile(logo_path):
        try:
            pdf.set_xy(margin, left_y)
            pdf.image(logo_path, w=30)
            left_y = pdf.get_y() + 2
        except Exception:
            pass

    pdf.set_xy(margin, left_y)
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.set_text_color(0, 0, 0)
    co_name = b.get("co_name", "")
    if co_name:
        pdf.cell(col_left_w, 6, co_name)
        left_y += 6

    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(80, 80, 80)
    city_line = " ".join(filter(None, [
        b.get("co_postal", ""), b.get("co_city", ""), b.get("co_country", ""),
    ]))
    for line_text in [b.get("co_address", ""), city_line,
                      b.get("co_phone", ""), b.get("co_email", "")]:
        if line_text.strip():
            pdf.set_xy(margin, left_y)
            pdf.cell(col_left_w, 5, line_text)
            left_y += 5

    # --- Right column: document title, number, date ---
    right_y = start_y

    pdf.set_xy(col_right_x, right_y)
    pdf.set_font("Helvetica", style="B", size=14)
    pdf.set_text_color(*theme)
    pdf.cell(col_right_w, 8, title, align="R")
    right_y += 8

    pdf.set_xy(col_right_x, right_y)
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.cell(col_right_w, 7, doc_number, align="R")
    right_y += 7

    pdf.set_xy(col_right_x, right_y)
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(col_right_w, 5, f"Date: {doc_date}", align="R")
    right_y += 5

    # Move below both columns, draw horizontal rule
    bottom_y = max(left_y, right_y) + 4
    pdf.set_y(bottom_y)
    pdf.set_draw_color(*theme)
    pdf.set_line_width(0.5)
    pdf.line(margin, bottom_y, pdf.w - pdf.r_margin, bottom_y)
    pdf.set_line_width(0.2)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)


def export_wz(wz_id: int) -> str:
    """Generate a branded PDF for a WZ delivery note. Returns the saved file path."""
    import data.wz as wzdata
    import data.customers as cdata

    hdr = wzdata.get_by_pk(wz_id)
    if not hdr:
        raise ValueError(f"WZ #{wz_id} not found.")
    items = wzdata.fetch_items(wz_id)
    customer = cdata.get_by_pk(hdr["CustomerID"]) if hdr.get("CustomerID") else {}
    b = _branding()
    sym = get_currency_symbol()
    show_prices = b.get("doc_wz_show_prices", "true").lower() != "false"
    theme = _theme_colour(b.get("doc_theme", ""))

    pdf = _NorthwindPDF(footer_text=b.get("doc_footer", ""), theme_rgb=theme)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    title = b.get("doc_title_wz") or "Delivery Note"
    doc_number = hdr.get("WZ_Number", f"WZ-{wz_id}")
    doc_date = hdr.get("WZ_Date", "")
    _draw_header(pdf, b, title, doc_number, doc_date)

    margin = pdf.l_margin
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    cust = customer or {}

    # --- Ship To box ---
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_text_color(80, 80, 80)
    pdf.set_x(margin)
    pdf.cell(0, 5, "SHIP TO:", new_x="LMARGIN", new_y="NEXT")

    box_y = pdf.get_y()
    box_h = 28
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(margin, box_y, page_w, box_h, style="F")

    inner_y = box_y + 3
    pdf.set_font("Helvetica", style="B", size=10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(margin + 3, inner_y)
    pdf.cell(page_w - 6, 5, cust.get("CompanyName", hdr.get("CompanyName", "")))
    inner_y += 5

    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(50, 50, 50)
    city_line = " ".join(filter(None, [
        cust.get("PostalCode", ""), cust.get("City", ""), cust.get("Country", ""),
    ]))
    for line_text in [cust.get("Address", ""), city_line]:
        if line_text.strip():
            pdf.set_xy(margin + 3, inner_y)
            pdf.cell(page_w - 6, 5, line_text)
            inner_y += 5

    pdf.set_y(box_y + box_h + 4)

    # --- Source order / Notes ---
    if hdr.get("OrderID"):
        pdf.set_font("Helvetica", size=9)
        pdf.set_text_color(60, 60, 60)
        pdf.set_x(margin)
        pdf.cell(0, 5, f"Source Sales Order: #{hdr['OrderID']}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    if hdr.get("Notes"):
        pdf.set_font("Helvetica", style="I", size=9)
        pdf.set_text_color(60, 60, 60)
        pdf.set_x(margin)
        pdf.cell(0, 5, f"Notes: {hdr['Notes']}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    pdf.ln(3)

    # --- Line items table ---
    if show_prices:
        col_widths = [8, page_w - 8 - 14 - 24 - 24, 14, 24, 24]
        headers = ["#", "Product Name", "Qty", "Unit Price", "Line Total"]
    else:
        col_widths = [8, page_w - 8 - 14, 14]
        headers = ["#", "Product Name", "Qty"]

    row_h = 7

    # Table header row
    pdf.set_fill_color(*theme)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_x(margin)
    for i, (h, w) in enumerate(zip(headers, col_widths)):
        align = "R" if i >= 2 else "L"
        pdf.cell(w, row_h, h, border=0, align=align, fill=True)
    pdf.ln()

    # Data rows
    total = 0.0
    pdf.set_font("Helvetica", size=9)
    for idx, it in enumerate(items):
        fill = (idx % 2 == 1)
        if fill:
            pdf.set_fill_color(245, 248, 252)
        pdf.set_text_color(0, 0, 0)
        lt = it.get("LineTotal") or 0.0
        total += lt
        row_data = [str(idx + 1), it["ProductName"], str(it["Quantity"])]
        if show_prices:
            row_data += [f"{sym}{it['UnitPrice']:.2f}", f"{sym}{lt:.2f}"]
        pdf.set_x(margin)
        for i, (val, w) in enumerate(zip(row_data, col_widths)):
            align = "R" if i >= 2 else "L"
            pdf.cell(w, row_h, val, border=0, align=align, fill=fill)
        pdf.ln()

    # Total row
    if show_prices and items:
        pdf.set_fill_color(225, 225, 225)
        pdf.set_font("Helvetica", style="B", size=9)
        pdf.set_text_color(0, 0, 0)
        pdf.set_x(margin)
        for i in range(len(col_widths) - 2):
            pdf.cell(col_widths[i], row_h, "", border=0, fill=True)
        pdf.cell(col_widths[-2], row_h, "TOTAL", align="R", border=0, fill=True)
        pdf.cell(col_widths[-1], row_h, f"{sym}{total:.2f}", align="R", border=0, fill=True)
        pdf.ln()

    # --- VAT / Tax band ---
    pdf.ln(4)
    if b.get("co_vat") or b.get("co_tax_id"):
        vat_parts = []
        if b.get("co_vat"):
            vat_parts.append(f"VAT No: {b['co_vat']}")
        if b.get("co_tax_id"):
            vat_parts.append(f"Tax ID: {b['co_tax_id']}")
        vat_y = pdf.get_y()
        pdf.set_fill_color(245, 245, 245)
        pdf.rect(margin, vat_y, page_w, 8, style="F")
        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(100, 100, 100)
        pdf.set_xy(margin + 3, vat_y + 1.5)
        pdf.cell(page_w - 6, 5, "   |   ".join(vat_parts))

    # --- Save ---
    downloads = os.path.expanduser("~/Downloads")
    os.makedirs(downloads, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_number = doc_number.replace("/", "-").replace("\\", "-")
    path = os.path.join(downloads, f"northwind_wz_{safe_number}_{ts}.pdf")
    pdf.output(path)
    return path


def export_fv(fv_id: int) -> str:
    """Generate a branded PDF for an FV invoice. Returns the saved file path."""
    import data.fv as fvdata
    import data.customers as cdata

    hdr = fvdata.get_by_pk(fv_id)
    if not hdr:
        raise ValueError(f"FV #{fv_id} not found.")
    items = fvdata.fetch_line_items(fv_id)
    linked_wz = fvdata.fetch_linked_wz(fv_id)
    customer = cdata.get_by_pk(hdr["CustomerID"]) if hdr.get("CustomerID") else {}
    b = _branding()
    sym = get_currency_symbol()
    theme = _theme_colour(b.get("doc_theme", ""))

    pdf = _NorthwindPDF(footer_text=b.get("doc_footer", ""), theme_rgb=theme)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    title = b.get("doc_title_fv") or "Invoice"
    doc_number = hdr.get("FV_Number", f"FV-{fv_id}")
    doc_date = hdr.get("FV_Date", "")
    _draw_header(pdf, b, title, doc_number, doc_date)

    margin = pdf.l_margin
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    cust = customer or {}

    # --- Two-column section: Bill To (left) + Payment Details (right) ---
    section_y = pdf.get_y()
    left_col_w = 90
    gap = 5
    right_col_x = margin + left_col_w + gap
    right_col_w = pdf.w - pdf.r_margin - right_col_x
    box_h = 32

    # "BILL TO" label
    pdf.set_xy(margin, section_y)
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(left_col_w, 5, "BILL TO:")

    # "PAYMENT DETAILS" label
    pdf.set_xy(right_col_x, section_y)
    pdf.cell(right_col_w, 5, "PAYMENT DETAILS:", align="R")

    bill_y = section_y + 5
    pay_y = section_y + 5

    # Bill To box
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(margin, bill_y, left_col_w, box_h, style="F")

    inner_y = bill_y + 3
    pdf.set_font("Helvetica", style="B", size=10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(margin + 3, inner_y)
    pdf.cell(left_col_w - 6, 5, cust.get("CompanyName", hdr.get("CompanyName", "")))
    inner_y += 5

    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(50, 50, 50)
    city_line = " ".join(filter(None, [
        cust.get("PostalCode", ""), cust.get("City", ""), cust.get("Country", ""),
    ]))
    for line_text in [cust.get("ContactName", ""), cust.get("Address", ""), city_line]:
        if line_text.strip():
            pdf.set_xy(margin + 3, inner_y)
            pdf.cell(left_col_w - 6, 5, line_text)
            inner_y += 5

    # Payment Details box
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(right_col_x, pay_y, right_col_w, box_h, style="F")

    inner_pay_y = pay_y + 3
    for label, val in [
        ("Due Date:", hdr.get("DueDate") or ""),
        ("Terms:", f"{hdr.get('PaymentTermDays') or 0} days"),
        ("Method:", hdr.get("PaymentMethod") or ""),
        ("Bank:", b.get("co_bank_account", "")),
    ]:
        if val and val.strip():
            pdf.set_xy(right_col_x + 3, inner_pay_y)
            pdf.set_font("Helvetica", style="B", size=9)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(22, 5, label)
            pdf.set_font("Helvetica", size=9)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(right_col_w - 28, 5, str(val), align="R")
            inner_pay_y += 5

    pdf.set_y(section_y + 5 + box_h + 6)

    # --- Line items table ---
    col_widths = [8, page_w - 8 - 14 - 24 - 24, 14, 24, 24]
    headers = ["#", "Product Name", "Qty", "Unit Price", "Line Total"]
    row_h = 7

    pdf.set_fill_color(*theme)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_x(margin)
    for i, (h, w) in enumerate(zip(headers, col_widths)):
        align = "R" if i >= 2 else "L"
        pdf.cell(w, row_h, h, border=0, align=align, fill=True)
    pdf.ln()

    total_net = 0.0
    pdf.set_font("Helvetica", size=9)
    for idx, it in enumerate(items):
        fill = (idx % 2 == 1)
        if fill:
            pdf.set_fill_color(245, 248, 252)
        pdf.set_text_color(0, 0, 0)
        lt = it.get("LineTotal") or 0.0
        total_net += lt
        row_data = [
            str(idx + 1),
            it["ProductName"],
            str(it["Quantity"]),
            f"{sym}{it['UnitPrice']:.2f}",
            f"{sym}{lt:.2f}",
        ]
        pdf.set_x(margin)
        for i, (val, w) in enumerate(zip(row_data, col_widths)):
            align = "R" if i >= 2 else "L"
            pdf.cell(w, row_h, val, border=0, align=align, fill=fill)
        pdf.ln()

    pdf.ln(4)

    # --- Totals block (right-aligned) ---
    total_net_db = hdr.get("TotalNet") or total_net
    paid = hdr.get("PaidAmount") or 0.0
    outstanding = hdr.get("Outstanding")
    if outstanding is None:
        outstanding = total_net_db - paid

    totals_x = margin + page_w * 0.55
    totals_label_w = page_w * 0.25
    totals_val_w = page_w * 0.20

    pdf.set_font("Helvetica", style="B", size=10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_x(totals_x)
    pdf.cell(totals_label_w, 6, "Total Net:", align="L")
    pdf.cell(totals_val_w, 6, f"{sym}{total_net_db:.2f}", align="R")
    pdf.ln()

    if paid > 0:
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(34, 139, 34)
        pdf.set_x(totals_x)
        pdf.cell(totals_label_w, 6, "Paid:", align="L")
        pdf.cell(totals_val_w, 6, f"{sym}{paid:.2f}", align="R")
        pdf.ln()

    pdf.set_font("Helvetica", style="B", size=10)
    if outstanding > 0:
        pdf.set_text_color(200, 30, 30)
    else:
        pdf.set_text_color(34, 139, 34)
    pdf.set_x(totals_x)
    pdf.cell(totals_label_w, 6, "Outstanding:", align="L")
    pdf.cell(totals_val_w, 6, f"{sym}{outstanding:.2f}", align="R")
    pdf.ln()

    # --- Linked WZ references ---
    if linked_wz:
        pdf.ln(3)
        wz_numbers = ", ".join(w["WZ_Number"] for w in linked_wz)
        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(120, 120, 120)
        pdf.set_x(margin)
        pdf.cell(0, 5, f"Based on WZ: {wz_numbers}", new_x="LMARGIN", new_y="NEXT")

    # --- Legal footer: VAT / Tax ID ---
    if b.get("co_vat") or b.get("co_tax_id"):
        pdf.ln(2)
        vat_parts = []
        if b.get("co_vat"):
            vat_parts.append(f"VAT No: {b['co_vat']}")
        if b.get("co_tax_id"):
            vat_parts.append(f"Tax ID: {b['co_tax_id']}")
        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(120, 120, 120)
        pdf.set_x(margin)
        pdf.cell(0, 5, "   |   ".join(vat_parts), new_x="LMARGIN", new_y="NEXT")

    # --- Save ---
    downloads = os.path.expanduser("~/Downloads")
    os.makedirs(downloads, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_number = doc_number.replace("/", "-").replace("\\", "-")
    path = os.path.join(downloads, f"northwind_fv_{safe_number}_{ts}.pdf")
    pdf.output(path)
    return path
