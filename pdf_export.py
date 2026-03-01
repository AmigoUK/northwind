"""pdf_export.py — PDF generation for all Northwind documents."""
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
        "doc_title_dn", "doc_title_inv", "doc_title_cn", "doc_dn_show_prices",
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


def export_dn(dn_id: int, save_path: str | None = None) -> str:
    """Generate a branded PDF for a DN delivery note. Returns the saved file path."""
    import data.dn as dndata
    import data.customers as cdata

    hdr = dndata.get_by_pk(dn_id)
    if not hdr:
        raise ValueError(f"DN #{dn_id} not found.")
    items = dndata.fetch_items(dn_id)
    customer = cdata.get_by_pk(hdr["CustomerID"]) if hdr.get("CustomerID") else {}
    b = _branding()
    sym = get_currency_symbol()
    show_prices = b.get("doc_dn_show_prices", "true").lower() != "false"
    theme = _theme_colour(b.get("doc_theme", ""))

    pdf = _NorthwindPDF(footer_text=b.get("doc_footer", ""), theme_rgb=theme)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    title = b.get("doc_title_dn") or "Delivery Note"
    doc_number = hdr.get("DN_Number", f"DN-{dn_id}")
    doc_date = hdr.get("DN_Date", "")
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

    return _save_pdf(pdf, "dn", doc_number, save_path)


def export_inv(inv_id: int, save_path: str | None = None) -> str:
    """Generate a branded PDF for an INV invoice. Returns the saved file path."""
    import data.inv as invdata
    import data.customers as cdata

    hdr = invdata.get_by_pk(inv_id)
    if not hdr:
        raise ValueError(f"INV #{inv_id} not found.")
    items = invdata.fetch_line_items(inv_id)
    linked_wz = invdata.fetch_linked_dn(inv_id)
    customer = cdata.get_by_pk(hdr["CustomerID"]) if hdr.get("CustomerID") else {}
    b = _branding()
    sym = get_currency_symbol()
    theme = _theme_colour(b.get("doc_theme", ""))

    pdf = _NorthwindPDF(footer_text=b.get("doc_footer", ""), theme_rgb=theme)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    title = b.get("doc_title_inv") or "Invoice"
    doc_number = hdr.get("INV_Number", f"INV-{inv_id}")
    doc_date = hdr.get("INV_Date", "")
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

    # --- Linked DN references ---
    if linked_wz:
        pdf.ln(3)
        dn_numbers = ", ".join(w["DN_Number"] for w in linked_wz)
        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(120, 120, 120)
        pdf.set_x(margin)
        pdf.cell(0, 5, f"Based on DN: {dn_numbers}", new_x="LMARGIN", new_y="NEXT")

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

    return _save_pdf(pdf, "inv", doc_number, save_path)


# ── Shared helpers for voucher-style single-entry documents ───────────────────

def _draw_field_row(pdf: _NorthwindPDF, margin: float, page_w: float,
                    label: str, value: str, label_w: float = 45) -> None:
    """Draw one labelled field row (label bold-grey, value black)."""
    if not value or not value.strip():
        return
    pdf.set_x(margin)
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(label_w, 6, label)
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(page_w - label_w, 6, value, new_x="LMARGIN", new_y="NEXT")


def _draw_amount_box(pdf: _NorthwindPDF, margin: float, page_w: float,
                     sym: str, amount: float, theme: tuple) -> None:
    """Draw a prominent centred amount box."""
    box_y = pdf.get_y()
    box_h = 18
    pdf.set_fill_color(*theme)
    pdf.rect(margin, box_y, page_w, box_h, style="F")
    pdf.set_font("Helvetica", style="B", size=18)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(margin, box_y + 3)
    pdf.cell(page_w, 12, f"{sym}{amount:,.2f}", align="C")
    pdf.set_y(box_y + box_h + 4)
    pdf.set_text_color(0, 0, 0)


def _draw_signature_line(pdf: _NorthwindPDF, margin: float, page_w: float,
                          theme: tuple) -> None:
    """Draw a signature line near the bottom."""
    pdf.ln(10)
    sig_x = margin + page_w * 0.55
    sig_w = page_w * 0.45
    pdf.set_draw_color(*theme)
    pdf.set_line_width(0.4)
    pdf.line(sig_x, pdf.get_y(), sig_x + sig_w, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_font("Helvetica", size=8)
    pdf.set_text_color(120, 120, 120)
    pdf.set_x(sig_x)
    pdf.cell(sig_w, 5, "Authorised signature", align="C")


def _save_pdf(pdf: _NorthwindPDF, prefix: str, doc_number: str, save_path: str | None = None) -> str:
    """Output PDF to save_path (if given) or ~/Downloads and return the path."""
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        pdf.output(save_path)
        return save_path
    downloads = os.path.expanduser("~/Downloads")
    os.makedirs(downloads, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = doc_number.replace("/", "-").replace("\\", "-")
    path = os.path.join(downloads, f"northwind_{prefix}_{safe}_{ts}.pdf")
    pdf.output(path)
    return path


# ── GR — Goods Receipt ────────────────────────────────────────────────────────

def export_gr(gr_id: int, save_path: str | None = None) -> str:
    """Generate a branded PDF for a GR goods receipt. Returns the saved file path."""
    import data.gr as grdata
    import data.suppliers as sdata

    hdr = grdata.get_by_pk(gr_id)
    if not hdr:
        raise ValueError(f"GR #{gr_id} not found.")
    items = grdata.fetch_items(gr_id)
    supplier = sdata.get_by_pk(hdr["SupplierID"]) if hdr.get("SupplierID") else {}
    b = _branding()
    sym = get_currency_symbol()
    theme = _theme_colour(b.get("doc_theme", ""))

    pdf = _NorthwindPDF(footer_text=b.get("doc_footer", ""), theme_rgb=theme)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    doc_number = hdr.get("GR_Number", f"GR-{gr_id}")
    doc_date = hdr.get("GR_Date", "")
    _draw_header(pdf, b, "Goods Receipt", doc_number, doc_date)

    margin = pdf.l_margin
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    sup = supplier or {}

    # --- Receive From box ---
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_text_color(80, 80, 80)
    pdf.set_x(margin)
    pdf.cell(0, 5, "RECEIVE FROM:", new_x="LMARGIN", new_y="NEXT")

    box_y = pdf.get_y()
    box_h = 28
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(margin, box_y, page_w, box_h, style="F")

    inner_y = box_y + 3
    pdf.set_font("Helvetica", style="B", size=10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(margin + 3, inner_y)
    pdf.cell(page_w - 6, 5, sup.get("CompanyName", hdr.get("CompanyName", "")))
    inner_y += 5

    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(50, 50, 50)
    city_line = " ".join(filter(None, [
        sup.get("PostalCode", ""), sup.get("City", ""), sup.get("Country", ""),
    ]))
    for line_text in [sup.get("ContactName", ""), sup.get("Address", ""), city_line]:
        if line_text.strip():
            pdf.set_xy(margin + 3, inner_y)
            pdf.cell(page_w - 6, 5, line_text)
            inner_y += 5

    pdf.set_y(box_y + box_h + 4)

    # --- Meta fields ---
    if hdr.get("SupplierDocRef"):
        _draw_field_row(pdf, margin, page_w, "Supplier Ref:", hdr["SupplierDocRef"])
    if hdr.get("PaymentMethod"):
        _draw_field_row(pdf, margin, page_w, "Payment Method:", hdr["PaymentMethod"])
    if hdr.get("Notes"):
        _draw_field_row(pdf, margin, page_w, "Notes:", hdr["Notes"])

    pdf.ln(3)

    # --- Line items table ---
    col_widths = [8, page_w - 8 - 14 - 24 - 24, 14, 24, 24]
    headers = ["#", "Product Name", "Qty", "Unit Cost", "Line Total"]
    row_h = 7

    pdf.set_fill_color(*theme)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_x(margin)
    for i, (h, w) in enumerate(zip(headers, col_widths)):
        pdf.cell(w, row_h, h, border=0, align="R" if i >= 2 else "L", fill=True)
    pdf.ln()

    total = 0.0
    pdf.set_font("Helvetica", size=9)
    for idx, it in enumerate(items):
        fill = (idx % 2 == 1)
        if fill:
            pdf.set_fill_color(245, 248, 252)
        pdf.set_text_color(0, 0, 0)
        lt = it.get("LineTotal") or 0.0
        total += lt
        row_data = [
            str(idx + 1), it["ProductName"], str(it["Quantity"]),
            f"{sym}{it['UnitCost']:.2f}", f"{sym}{lt:.2f}",
        ]
        pdf.set_x(margin)
        for i, (val, w) in enumerate(zip(row_data, col_widths)):
            pdf.cell(w, row_h, val, border=0, align="R" if i >= 2 else "L", fill=fill)
        pdf.ln()

    # Total row
    pdf.set_fill_color(225, 225, 225)
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_text_color(0, 0, 0)
    pdf.set_x(margin)
    for i in range(len(col_widths) - 2):
        pdf.cell(col_widths[i], row_h, "", border=0, fill=True)
    pdf.cell(col_widths[-2], row_h, "TOTAL COST", align="R", border=0, fill=True)
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

    return _save_pdf(pdf, "gr", doc_number, save_path)


# ── CR — Cash Receipt ─────────────────────────────────────────────────────────

def export_cr(cr_id: int, save_path: str | None = None) -> str:
    """Generate a branded PDF for a CR cash receipt. Returns the saved file path."""
    import data.cash as cashdata
    import data.customers as cdata

    hdr = cashdata.get_cr_by_pk(cr_id)
    if not hdr:
        raise ValueError(f"CR #{cr_id} not found.")
    customer = cdata.get_by_pk(hdr["CustomerID"]) if hdr.get("CustomerID") else {}
    b = _branding()
    sym = get_currency_symbol()
    theme = _theme_colour(b.get("doc_theme", ""))

    pdf = _NorthwindPDF(footer_text=b.get("doc_footer", ""), theme_rgb=theme)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    doc_number = hdr.get("CR_Number", f"CR-{cr_id}")
    doc_date = hdr.get("CR_Date", "")
    _draw_header(pdf, b, "Cash Receipt", doc_number, doc_date)

    margin = pdf.l_margin
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    cust = customer or {}

    # --- Party / reference fields ---
    cust_name = cust.get("CompanyName") or hdr.get("CompanyName", "")
    if cust_name:
        _draw_field_row(pdf, margin, page_w, "Received From:", cust_name)
    if hdr.get("INV_ID"):
        _draw_field_row(pdf, margin, page_w, "INV Reference:", f"INV #{hdr['INV_ID']}")
    if hdr.get("Description"):
        _draw_field_row(pdf, margin, page_w, "Description:", hdr["Description"])

    pdf.ln(5)

    # --- Amount box ---
    _draw_amount_box(pdf, margin, page_w, sym, hdr.get("Amount") or 0.0, theme)

    _draw_signature_line(pdf, margin, page_w, theme)

    return _save_pdf(pdf, "cr", doc_number, save_path)


# ── CP — Cash Payment ─────────────────────────────────────────────────────────

def export_cp(cp_id: int, save_path: str | None = None) -> str:
    """Generate a branded PDF for a CP cash payment. Returns the saved file path."""
    import data.cash as cashdata
    import data.suppliers as sdata

    hdr = cashdata.get_cp_by_pk(cp_id)
    if not hdr:
        raise ValueError(f"CP #{cp_id} not found.")
    supplier = sdata.get_by_pk(hdr["SupplierID"]) if hdr.get("SupplierID") else {}
    b = _branding()
    sym = get_currency_symbol()
    theme = _theme_colour(b.get("doc_theme", ""))

    pdf = _NorthwindPDF(footer_text=b.get("doc_footer", ""), theme_rgb=theme)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    doc_number = hdr.get("CP_Number", f"CP-{cp_id}")
    doc_date = hdr.get("CP_Date", "")
    _draw_header(pdf, b, "Cash Payment", doc_number, doc_date)

    margin = pdf.l_margin
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    sup = supplier or {}

    sup_name = sup.get("CompanyName") or hdr.get("CompanyName", "")
    if sup_name:
        _draw_field_row(pdf, margin, page_w, "Paid To:", sup_name)
    if hdr.get("GR_ID"):
        _draw_field_row(pdf, margin, page_w, "GR Reference:", f"GR #{hdr['GR_ID']}")
    if hdr.get("Description"):
        _draw_field_row(pdf, margin, page_w, "Description:", hdr["Description"])

    pdf.ln(5)

    _draw_amount_box(pdf, margin, page_w, sym, hdr.get("Amount") or 0.0, theme)

    _draw_signature_line(pdf, margin, page_w, theme)

    return _save_pdf(pdf, "cp", doc_number, save_path)


# ── Bank Entry ────────────────────────────────────────────────────────────────

def export_bank_entry(entry_id: int, save_path: str | None = None) -> str:
    """Generate a branded PDF for a Bank Account entry. Returns the saved file path."""
    import data.bank as bankdata

    hdr = bankdata.get_by_pk(entry_id)
    if not hdr:
        raise ValueError(f"Bank Entry #{entry_id} not found.")
    b = _branding()
    sym = get_currency_symbol()
    theme = _theme_colour(b.get("doc_theme", ""))

    direction = hdr.get("Direction", "in")
    title = "Bank Receipt" if direction == "in" else "Bank Payment"

    pdf = _NorthwindPDF(footer_text=b.get("doc_footer", ""), theme_rgb=theme)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    doc_number = hdr.get("Entry_Number", f"BANK-{entry_id}")
    doc_date = hdr.get("Entry_Date", "")
    _draw_header(pdf, b, title, doc_number, doc_date)

    margin = pdf.l_margin
    page_w = pdf.w - pdf.l_margin - pdf.r_margin

    # Direction badge
    badge_label = "MONEY IN" if direction == "in" else "MONEY OUT"
    badge_colour = (34, 139, 34) if direction == "in" else (200, 30, 30)
    badge_y = pdf.get_y()
    pdf.set_fill_color(*badge_colour)
    pdf.rect(margin, badge_y, 40, 8, style="F")
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(margin, badge_y + 1.5)
    pdf.cell(40, 5, badge_label, align="C")
    pdf.set_y(badge_y + 12)
    pdf.set_text_color(0, 0, 0)

    # Counterparty and reference fields
    counterparty = hdr.get("CustomerName") or hdr.get("SupplierName") or ""
    party_label = "Customer:" if hdr.get("CustomerName") else "Supplier:"
    if counterparty:
        _draw_field_row(pdf, margin, page_w, party_label, counterparty)
    if hdr.get("INV_ID"):
        _draw_field_row(pdf, margin, page_w, "INV Reference:", f"INV #{hdr['INV_ID']}")
    if hdr.get("GR_ID"):
        _draw_field_row(pdf, margin, page_w, "GR Reference:", f"GR #{hdr['GR_ID']}")
    if hdr.get("Description"):
        _draw_field_row(pdf, margin, page_w, "Description:", hdr["Description"])
    if b.get("co_bank_account"):
        _draw_field_row(pdf, margin, page_w, "Bank Account:", b["co_bank_account"])

    pdf.ln(5)

    _draw_amount_box(pdf, margin, page_w, sym, hdr.get("Amount") or 0.0, theme)

    _draw_signature_line(pdf, margin, page_w, theme)

    return _save_pdf(pdf, "bank", doc_number, save_path)


# ── CN — Credit Note ─────────────────────────────────────────────────────────

def export_cn(cn_id: int, save_path: str | None = None) -> str:
    """Generate a branded PDF for a CN credit note. Returns the saved file path."""
    import data.cn as cndata
    import data.customers as cdata

    hdr = cndata.get_by_pk(cn_id)
    if not hdr:
        raise ValueError(f"CN #{cn_id} not found.")
    items = cndata.fetch_items(cn_id)
    customer = cdata.get_by_pk(hdr["CustomerID"]) if hdr.get("CustomerID") else {}
    b = _branding()
    sym = get_currency_symbol()
    theme = _theme_colour(b.get("doc_theme", ""))

    pdf = _NorthwindPDF(footer_text=b.get("doc_footer", ""), theme_rgb=theme)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    title = b.get("doc_title_cn") or "Credit Note"
    doc_number = hdr.get("CN_Number", f"CN-{cn_id}")
    doc_date = hdr.get("CN_Date", "")
    _draw_header(pdf, b, title, doc_number, doc_date)

    margin = pdf.l_margin
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    cust = customer or {}

    # --- Cancellation banner ---
    if hdr.get("CN_Type") == "cancellation":
        banner_y = pdf.get_y()
        pdf.set_fill_color(200, 30, 30)
        pdf.rect(margin, banner_y, page_w, 10, style="F")
        pdf.set_font("Helvetica", style="B", size=14)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(margin, banner_y + 1.5)
        pdf.cell(page_w, 7, "CANCELLATION", align="C")
        pdf.set_y(banner_y + 14)
        pdf.set_text_color(0, 0, 0)

    # --- Two-column section: Customer (left) + CN Details (right) ---
    section_y = pdf.get_y()
    left_col_w = 90
    gap = 5
    right_col_x = margin + left_col_w + gap
    right_col_w = pdf.w - pdf.r_margin - right_col_x
    box_h = 28

    pdf.set_xy(margin, section_y)
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(left_col_w, 5, "CUSTOMER:")

    pdf.set_xy(right_col_x, section_y)
    pdf.cell(right_col_w, 5, "CORRECTION DETAILS:", align="R")

    bill_y = section_y + 5
    detail_y = section_y + 5

    # Customer box
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
    for line_text in [cust.get("Address", ""), city_line]:
        if line_text and line_text.strip():
            pdf.set_xy(margin + 3, inner_y)
            pdf.cell(left_col_w - 6, 5, line_text)
            inner_y += 5

    # CN details box
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(right_col_x, detail_y, right_col_w, box_h, style="F")

    cn_type_labels = {
        "full_reversal": "Full Reversal",
        "partial_correction": "Partial Correction",
        "cancellation": "Cancellation",
    }
    inner_d_y = detail_y + 3
    for label, val in [
        ("Original INV:", hdr.get("INV_Number", "")),
        ("Type:", cn_type_labels.get(hdr.get("CN_Type", ""), hdr.get("CN_Type", ""))),
        ("Status:", (hdr.get("Status") or "").capitalize()),
    ]:
        if val and str(val).strip():
            pdf.set_xy(right_col_x + 3, inner_d_y)
            pdf.set_font("Helvetica", style="B", size=9)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(22, 5, label)
            pdf.set_font("Helvetica", size=9)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(right_col_w - 28, 5, str(val), align="R")
            inner_d_y += 5

    pdf.set_y(section_y + 5 + box_h + 4)

    # --- Reason ---
    if hdr.get("Reason"):
        pdf.set_font("Helvetica", style="B", size=9)
        pdf.set_text_color(80, 80, 80)
        pdf.set_x(margin)
        pdf.cell(25, 5, "Reason:")
        pdf.set_font("Helvetica", size=9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(page_w - 25, 5, hdr["Reason"], new_x="LMARGIN", new_y="NEXT")

    if hdr.get("Notes"):
        pdf.set_font("Helvetica", style="I", size=9)
        pdf.set_text_color(60, 60, 60)
        pdf.set_x(margin)
        pdf.cell(0, 5, f"Notes: {hdr['Notes']}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)

    # --- Correction items table ---
    # Columns: #, Product, Orig Qty, Corr Qty, Orig Price, Corr Price, Orig Total, Corr Total, Correction
    c1 = 6                           # #
    c9 = 20                          # Correction
    c8 = 20                          # Corr Total
    c7 = 20                          # Orig Total
    c6 = 18                          # Corr Price
    c5 = 18                          # Orig Price
    c4 = 12                          # Corr Qty
    c3 = 12                          # Orig Qty
    c2 = page_w - c1 - c3 - c4 - c5 - c6 - c7 - c8 - c9  # Product
    col_widths = [c1, c2, c3, c4, c5, c6, c7, c8, c9]
    headers = ["#", "Product", "O.Qty", "C.Qty", "O.Price", "C.Price",
               "O.Total", "C.Total", "Corr."]
    row_h = 7

    pdf.set_fill_color(*theme)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", style="B", size=8)
    pdf.set_x(margin)
    for i, (h, w) in enumerate(zip(headers, col_widths)):
        align = "R" if i >= 2 else "L"
        pdf.cell(w, row_h, h, border=0, align=align, fill=True)
    pdf.ln()

    total_correction = 0.0
    pdf.set_font("Helvetica", size=8)
    for idx, it in enumerate(items):
        fill = (idx % 2 == 1)
        if fill:
            pdf.set_fill_color(245, 248, 252)
        pdf.set_text_color(0, 0, 0)

        orig_qty = it.get("OrigQuantity", 0)
        corr_qty = it.get("CorrQuantity", 0)
        orig_price = it.get("OrigUnitPrice", 0)
        corr_price = it.get("CorrUnitPrice", 0)
        orig_total = orig_qty * orig_price
        corr_total = corr_qty * corr_price
        line_corr = it.get("LineCorrection", 0)
        total_correction += line_corr

        row_data = [
            str(idx + 1),
            it.get("ProductName", ""),
            str(orig_qty),
            str(corr_qty),
            f"{sym}{orig_price:.2f}",
            f"{sym}{corr_price:.2f}",
            f"{sym}{orig_total:.2f}",
            f"{sym}{corr_total:.2f}",
            f"{sym}{line_corr:.2f}",
        ]
        pdf.set_x(margin)
        for i, (val, w) in enumerate(zip(row_data, col_widths)):
            align = "R" if i >= 2 else "L"
            pdf.cell(w, row_h, val, border=0, align=align, fill=fill)
        pdf.ln()

    # Total correction row
    pdf.set_fill_color(225, 225, 225)
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_text_color(0, 0, 0)
    pdf.set_x(margin)
    pre_w = sum(col_widths[:-1])
    pdf.cell(pre_w, row_h, "TOTAL CORRECTION", align="R", border=0, fill=True)
    corr_colour = (200, 30, 30) if total_correction < 0 else (34, 139, 34)
    pdf.set_text_color(*corr_colour)
    pdf.cell(col_widths[-1], row_h, f"{sym}{total_correction:.2f}", align="R",
             border=0, fill=True)
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

    _draw_signature_line(pdf, margin, page_w, theme)

    return _save_pdf(pdf, "cn", doc_number, save_path)
