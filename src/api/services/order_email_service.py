# src/api/services/order_email_service.py
"""
Service for sending order notification emails to shop owners and admin users.
Uses the same invoice HTML design as the Go cron implementation.
"""
import os
from typing import List, Dict, Any
from src.api.core.utility import now_pk
from sqlmodel import Session, select

from src.api.models.order_model.orderModel import Order, OrderProduct
from src.api.models.shop_model.shopsModel import Shop
from src.api.models.usersModel import User
from src.api.core.email_helper import EmailHelper


class OrderEmailService:
    """Service to send order emails to shop owners and admin users."""

    def __init__(self):
        self.email_helper = EmailHelper()

    # ─── Shared helpers ────────────────────────────────────────────────────

    def _base_url(self) -> str:
        return os.getenv('DOMAIN', os.getenv('BASE_URL', 'https://shop.ghertak.com'))

    def _format_address(self, address_data: Any) -> str:
        if not address_data:
            return "Not provided"
        if isinstance(address_data, str):
            return address_data
        if isinstance(address_data, dict):
            keys = ['street', 'street_address', 'address', 'city', 'state', 'zip', 'zip_code', 'country']
            parts = [str(address_data[k]) for k in keys if address_data.get(k)]
            return ", ".join(parts) if parts else "Not provided"
        return str(address_data)

    def _resolve_customer(self, session: Session, order: Order):
        name = order.customer_name or "Guest"
        contact = order.customer_contact or "Not provided"
        email = "Not provided"
        if order.customer_id:
            user = session.get(User, order.customer_id)
            if user:
                email = user.email or email
                if not order.customer_name:
                    name = user.name or name
        return name, email, contact

    # ─── Product rows HTML (shared by shop-owner and admin) ────────────────

    def _product_table_rows(self, products: List[OrderProduct]) -> str:
        rows = ""
        for i, p in enumerate(products):
            img = "https://placehold.co/70x70/667eea/ffffff?text=IMG"
            name = "Unknown Product"
            sku = "N/A"
            variation = ""
            unit_price = float(p.unit_price or 0)
            subtotal = float(p.subtotal or 0)

            if p.product_snapshot and isinstance(p.product_snapshot, dict):
                name = p.product_snapshot.get("name", name)
                sku = p.product_snapshot.get("sku", sku)
                image_data = p.product_snapshot.get("image")
                if isinstance(image_data, dict):
                    img = image_data.get("thumbnail") or image_data.get("original") or img
                elif isinstance(image_data, str):
                    img = image_data

            if p.variation_data and isinstance(p.variation_data, dict):
                variation = p.variation_data.get("title", "")
            if not variation and p.variation_snapshot and isinstance(p.variation_snapshot, dict):
                variation = p.variation_snapshot.get("title", "")

            row_bg = "#ffffff" if i % 2 == 0 else "#f8f9fa"
            variation_cell = (
                f'<br><span style="font-size:11px;color:#667eea;font-style:italic;">{variation}</span>'
                if variation else ""
            )
            sale_badge = ""
            sale_price = float(p.sale_price) if p.sale_price else None
            if sale_price and sale_price > 0 and sale_price < unit_price:
                sale_badge = (
                    f'<br><span style="font-size:11px;color:#dc3545;text-decoration:line-through;">'
                    f'Rs.{unit_price:,.2f}</span>'
                )
                unit_price = sale_price

            try:
                qty_str = f"{int(float(p.order_quantity)):,}"
            except (ValueError, TypeError):
                qty_str = str(p.order_quantity)

            rows += f"""
<tr style="background:{row_bg};">
  <td style="padding:10px 8px;border-bottom:1px solid #e9ecef;vertical-align:middle;">
    <table cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="vertical-align:middle;padding-right:10px;">
        <img src="{img}" alt="{name}" width="60" height="60"
             style="border-radius:6px;object-fit:cover;border:1px solid #e2e8f0;display:block;" />
      </td>
      <td style="vertical-align:middle;">
        <div style="font-weight:600;color:#1a202c;font-size:14px;">{name}</div>
        <div style="font-size:12px;color:#718096;margin-top:3px;">SKU: {sku}</div>
        {variation_cell}
      </td>
    </tr></table>
  </td>
  <td style="padding:10px 8px;border-bottom:1px solid #e9ecef;text-align:center;font-size:13px;
             color:#4a5568;vertical-align:middle;"><strong>{qty_str}</strong></td>
  <td style="padding:10px 8px;border-bottom:1px solid #e9ecef;text-align:right;font-size:13px;
             color:#4a5568;vertical-align:middle;">Rs.{unit_price:,.2f}{sale_badge}</td>
  <td style="padding:10px 8px;border-bottom:1px solid #e9ecef;text-align:right;font-weight:700;
             font-size:14px;color:#667eea;vertical-align:middle;">Rs.{subtotal:,.2f}</td>
</tr>"""
        return rows

    # ─── Wallet breakdown HTML ──────────────────────────────────────────────

    @staticmethod
    def _wallet_html(total: float, wallet_amount_used: float, gateway: str) -> str:
        if not wallet_amount_used or wallet_amount_used <= 0:
            return ""
        gw = (gateway or "").replace("_", " ") or "Other"
        remainder = total - wallet_amount_used
        remainder_row = ""
        if remainder > 0.005:
            remainder_row = (
                f"<tr><td style='font-size:14px;color:#4a5568;padding:4px 0;'>Paid via {gw}</td>"
                f"<td style='font-size:14px;font-weight:700;color:#4a5568;"
                f"text-align:right;padding:4px 0;'>Rs.{remainder:,.2f}</td></tr>"
            )
        return (
            f'<div style="margin-top:16px;background:#f0fff4;border:1px solid #9ae6b4;'
            f'border-radius:8px;padding:16px 20px;">'
            f'<div style="font-size:13px;font-weight:700;color:#276749;margin-bottom:10px;">'
            f'&#128179; Payment Breakdown</div>'
            f'<table width="100%" cellpadding="0" cellspacing="0">'
            f"<tr><td style='font-size:14px;color:#4a5568;padding:4px 0;'>Paid via Wallet</td>"
            f"<td style='font-size:14px;font-weight:700;color:#38a169;"
            f"text-align:right;padding:4px 0;'>Rs.{wallet_amount_used:,.2f}</td></tr>"
            f"{remainder_row}"
            f"</table></div>"
        )

    # ─── Shop-owner totals rows ─────────────────────────────────────────────

    @staticmethod
    def _shop_totals_rows(subtotal: float, discount: float, tax: float, total: float) -> str:
        rows = f'<tr><td class="lbl">Subtotal</td><td class="val">Rs.{subtotal:,.2f}</td></tr>'
        if discount > 0:
            rows += (
                f'<tr><td class="lbl" style="color:#38a169;">Discount</td>'
                f'<td class="val" style="color:#38a169;">-Rs.{discount:,.2f}</td></tr>'
            )
        if tax > 0:
            rows += f'<tr><td class="lbl">Tax</td><td class="val">Rs.{tax:,.2f}</td></tr>'
        rows += (
            f'<tr class="grand-row"><td>Your Total</td>'
            f'<td style="text-align:right;color:#667eea;">Rs.{total:,.2f}</td></tr>'
        )
        return rows

    # ─── Admin summary rows ─────────────────────────────────────────────────

    @staticmethod
    def _admin_summary_rows(
        subtotal: float, discount: float, coupon_discount: float,
        delivery_fee: float, sales_tax: float, total: float
    ) -> str:
        tn = 'style="padding:10px 20px;font-size:14px;color:#4a5568;border-bottom:1px solid #e2e8f0;"'
        tr = 'style="padding:10px 20px;font-size:14px;text-align:right;color:#4a5568;border-bottom:1px solid #e2e8f0;"'
        tg = 'style="padding:10px 20px;font-size:14px;color:#38a169;border-bottom:1px solid #e2e8f0;"'
        tgr = 'style="padding:10px 20px;font-size:14px;text-align:right;color:#38a169;border-bottom:1px solid #e2e8f0;"'

        rows = f"<tr><td {tn}>Subtotal</td><td {tr}>Rs.{subtotal:,.2f}</td></tr>"
        if discount > 0:
            rows += f"<tr><td {tg}>Discount</td><td {tgr}>-Rs.{discount:,.2f}</td></tr>"
        if coupon_discount > 0:
            rows += f"<tr><td {tg}>Coupon Discount</td><td {tgr}>-Rs.{coupon_discount:,.2f}</td></tr>"
        if delivery_fee > 0:
            rows += f"<tr><td {tn}>Shipping Fee</td><td {tr}>Rs.{delivery_fee:,.2f}</td></tr>"
        if sales_tax > 0:
            rows += f"<tr><td {tn}>Tax</td><td {tr}>Rs.{sales_tax:,.2f}</td></tr>"
        rows += (
            f'<tr><td style="padding:16px 20px;font-size:20px;font-weight:800;color:#1a1a2e;'
            f'border-top:3px solid #667eea;">Grand Total</td>'
            f'<td style="padding:16px 20px;font-size:22px;font-weight:800;text-align:right;'
            f'color:#667eea;border-top:3px solid #667eea;">Rs.{total:,.2f}</td></tr>'
        )
        return rows

    # ─── Shop-owner email HTML ──────────────────────────────────────────────

    def _build_shop_owner_html(
        self, order: Order, shop: Shop, shop_products: List[OrderProduct],
        customer_name: str, customer_email: str, customer_contact: str, shipping_addr: str
    ) -> str:
        subtotal = sum(float(p.subtotal or 0) for p in shop_products)
        discount = sum(float(p.item_discount or 0) for p in shop_products)
        tax = sum(float(p.item_tax or 0) for p in shop_products)
        total = subtotal - discount + tax
        rows = self._product_table_rows(shop_products)
        totals_rows = self._shop_totals_rows(subtotal, discount, tax, total)
        order_date = order.created_at.strftime("%B %d, %Y %I:%M %p") if order.created_at else "N/A"
        dashboard_link = f"{self._base_url()}/dashboard/orders/{order.id}"
        print_link = f"{self._base_url()}/dashboard/orders/{order.id}/invoice"
        year = now_pk().year

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Invoice #{order.tracking_number} — {shop.name}</title>
<style>
body{{margin:0;padding:0;background:#f0f2f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;color:#333}}
table{{border-collapse:collapse}}
.wrap{{max-width:620px;margin:0 auto;background:#fff}}
.prod-table{{width:100%;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;font-size:13px}}
.prod-table thead tr{{background:#667eea;color:#fff}}
.prod-table th{{padding:10px 12px;text-align:left;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.5px}}
.prod-table th:last-child,.prod-table td:last-child{{text-align:right}}
.prod-table th:nth-child(2),.prod-table td:nth-child(2){{text-align:center}}
.prod-table th:nth-child(3),.prod-table td:nth-child(3){{text-align:right}}
.totals-table{{width:100%;margin-top:18px;font-size:14px}}
.totals-table td{{padding:7px 0}}
.lbl{{color:#718096}}
.val{{text-align:right;font-weight:600;color:#1a202c}}
.grand-row td{{border-top:2px solid #667eea;padding-top:12px;font-size:18px;font-weight:800;color:#1a1a2e}}
.cust-table{{width:100%;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin-top:4px}}
.cust-table td{{padding:10px 16px;font-size:13px;color:#4a5568;vertical-align:top}}
.cust-left{{background:#f7fafc;border-right:1px solid #e2e8f0;width:50%;font-weight:600;color:#2d3748}}
.cust-label{{font-size:11px;font-weight:700;color:#667eea;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}}
.sec-title{{font-size:15px;font-weight:700;color:#1a1a2e;border-bottom:2px solid #667eea;padding-bottom:8px;margin:24px 0 14px}}
@media print{{
  body{{background:#fff}}.wrap{{max-width:100%}}
  .action-bar,.status-row{{display:none}}
}}
</style>
</head>
<body>
<div class="wrap">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#1a1a2e;">
    <tr>
      <td style="padding:28px 30px;vertical-align:middle;">
        <div style="font-size:22px;font-weight:800;letter-spacing:1px;color:#fff;">CTSPK<span style="color:#667eea;">STORE</span></div>
        <div style="font-size:12px;color:#a0aec0;margin-top:4px;">Shop Order Invoice</div>
      </td>
      <td style="padding:28px 30px;text-align:right;vertical-align:middle;">
        <div style="display:inline-block;background:#667eea;color:#fff;font-size:11px;font-weight:700;padding:3px 12px;border-radius:20px;margin-bottom:6px;">INVOICE</div>
        <div style="font-size:15px;font-weight:700;color:#fff;">#{order.tracking_number}</div>
        <div style="font-size:12px;color:#a0aec0;margin-top:2px;">{order_date}</div>
      </td>
    </tr>
  </table>

  <div style="background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:14px 30px;">
    <div style="font-size:13px;opacity:.85;margin-bottom:2px;">Order for shop:</div>
    <div style="font-size:20px;font-weight:700;">{shop.name}</div>
  </div>

  <div class="status-row" style="background:#16213e;padding:10px 30px;">
    <span style="display:inline-block;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:600;text-transform:uppercase;background:#0f3460;color:#90cdf4;margin-right:8px;">Payment: {order.payment_status or 'Pending'}</span>
    <span style="display:inline-block;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:600;text-transform:uppercase;background:#1a3a1a;color:#68d391;">Order: {order.order_status or 'Pending'}</span>
  </div>

  <div style="padding:28px 30px;">
    <div class="sec-title">&#128230; Products in this Order</div>
    <table class="prod-table" cellpadding="0" cellspacing="0">
      <thead>
        <tr>
          <th style="width:55%;">Product</th>
          <th style="width:10%;">Qty</th>
          <th style="width:17%;">Unit Price</th>
          <th style="width:18%;">Total</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>

    <table class="totals-table" cellpadding="0" cellspacing="0">
      {totals_rows}
    </table>

    <div class="sec-title">&#128100; Customer &amp; Delivery</div>
    <table class="cust-table" cellpadding="0" cellspacing="0"><tr>
      <td class="cust-left">
        <div class="cust-label">&#128100; Customer</div>
        <div style="font-size:15px;margin-bottom:4px;">{customer_name}</div>
        <div>&#128222; {customer_contact}</div>
        <div>&#9993; {customer_email}</div>
      </td>
      <td>
        <div class="cust-label">&#128205; Shipping Address</div>
        <div>{shipping_addr}</div>
      </td>
    </tr></table>

    <div style="background:#fffbeb;border:1px solid #f6ad55;border-radius:6px;padding:12px 16px;font-size:13px;color:#744210;margin-top:20px;">
      <strong>&#9888; Important:</strong> Please process this order within 24 hours to ensure timely delivery.
    </div>

    <div class="action-bar" style="text-align:center;padding:20px 0 8px;">
      <a href="{dashboard_link}" style="display:inline-block;padding:11px 28px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;text-decoration:none;border-radius:6px;font-weight:700;font-size:14px;margin:4px;">View Order in Dashboard</a>
      <a href="{print_link}" style="display:inline-block;padding:11px 28px;background:#fff;color:#667eea;text-decoration:none;border-radius:6px;font-weight:700;font-size:14px;border:2px solid #667eea;margin:4px;">&#128438; Print Invoice</a>
    </div>
  </div>

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#1a1a2e;">
    <tr><td style="padding:22px 30px;text-align:center;color:#a0aec0;font-size:12px;">
      <p><strong style="color:#fff;">CTSPK Store</strong> &mdash; Shop Order Notification</p>
      <p style="margin-top:8px;"><a href="{dashboard_link}" style="color:#667eea;text-decoration:none;">Dashboard</a></p>
      <p style="margin-top:10px;font-size:11px;">&#169; {year} CTSPK Store. All rights reserved.</p>
    </td></tr>
  </table>
</div>
</body>
</html>"""

    # ─── Admin email HTML ───────────────────────────────────────────────────

    def _build_admin_html(
        self, order: Order, shop_groups: list,
        customer_name: str, customer_email: str, customer_contact: str,
        shipping_addr: str, billing_addr: str
    ) -> str:
        # Totals — match frontend: paid_total → total → amount
        all_products = [p for _, prods, _ in shop_groups for p in prods]
        subtotal = sum(float(p.subtotal or 0) for p in all_products)
        total = float(order.amount or 0)
        if order.total:
            total = float(order.total)
        if order.paid_total:
            total = float(order.paid_total)
        sales_tax = float(order.sales_tax or 0)
        discount = float(order.discount or 0)
        coupon_discount = float(order.coupon_discount or 0)
        delivery_fee = float(order.delivery_fee or 0)
        wallet_amount_used = float(order.wallet_amount_used or 0)
        gateway = str(order.payment_gateway or "")

        order_date = order.created_at.strftime("%B %d, %Y %I:%M %p") if order.created_at else "N/A"
        dashboard_link = f"{self._base_url()}/dashboard/orders/{order.id}"
        print_link = f"{self._base_url()}/dashboard/orders/{order.id}/invoice"
        year = now_pk().year

        summary_rows = self._admin_summary_rows(
            subtotal, discount, coupon_discount, delivery_fee, sales_tax, total
        )
        wallet_html = self._wallet_html(total, wallet_amount_used, gateway)

        # Per-shop product sections
        shop_sections = ""
        for group_name, products, sub in shop_groups:
            rows = self._product_table_rows(products)
            shop_sections += f"""
<div style="margin-bottom:24px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="border-radius:8px;overflow:hidden;border:1px solid #e2e8f0;">
    <thead>
      <tr style="background:#667eea;">
        <td colspan="4" style="padding:10px 14px;color:#fff;font-weight:700;font-size:14px;">
          &#127978; {group_name} &nbsp;&mdash;&nbsp; <span style="font-weight:400;font-size:13px;">Subtotal: Rs.{sub:,.2f}</span>
        </td>
      </tr>
      <tr style="background:#f0edff;">
        <th style="padding:9px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#667eea;font-weight:700;width:55%;">Product</th>
        <th style="padding:9px 12px;text-align:center;font-size:11px;color:#667eea;font-weight:700;width:10%;">Qty</th>
        <th style="padding:9px 12px;text-align:right;font-size:11px;color:#667eea;font-weight:700;width:17%;">Unit Price</th>
        <th style="padding:9px 12px;text-align:right;font-size:11px;color:#667eea;font-weight:700;width:18%;">Total</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
    <tfoot>
      <tr style="background:#f7fafc;">
        <td colspan="3" style="padding:10px 14px;text-align:right;font-size:13px;font-weight:600;color:#4a5568;">Shop Subtotal:</td>
        <td style="padding:10px 14px;text-align:right;font-size:14px;font-weight:800;color:#667eea;">Rs.{sub:,.2f}</td>
      </tr>
    </tfoot>
  </table>
</div>"""

        billing_html = ""
        if billing_addr and billing_addr != "Not provided":
            billing_html = (
                f'<div style="margin-top:12px;">'
                f'<div style="font-size:11px;font-weight:700;color:#667eea;text-transform:uppercase;'
                f'letter-spacing:.5px;margin-bottom:6px;">&#128196; Billing Address</div>'
                f'<div style="font-size:13px;color:#4a5568;">{billing_addr}</div></div>'
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Admin Invoice #{order.tracking_number}</title>
<style>
body{{margin:0;padding:0;background:#f0f2f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;color:#333}}
table{{border-collapse:collapse}}
.wrap{{max-width:680px;margin:0 auto;background:#fff}}
@media print{{
  body{{background:#fff}}.wrap{{max-width:100%}}
  .no-print{{display:none!important}}
  thead,tfoot{{page-break-inside:avoid}}
}}
</style>
</head>
<body>
<div class="wrap">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#1a1a2e;">
    <tr>
      <td style="padding:28px 30px;vertical-align:middle;">
        <div style="font-size:24px;font-weight:800;letter-spacing:1px;color:#fff;">CTSPK<span style="color:#667eea;">STORE</span></div>
        <div style="font-size:11px;color:#a0aec0;margin-top:4px;text-transform:uppercase;letter-spacing:1px;">Admin Order Invoice</div>
      </td>
      <td style="padding:28px 30px;text-align:right;vertical-align:middle;">
        <div style="display:inline-block;background:#667eea;color:#fff;font-size:11px;font-weight:700;padding:3px 14px;border-radius:20px;margin-bottom:6px;">INVOICE</div>
        <div style="font-size:18px;font-weight:700;color:#fff;">#{order.tracking_number}</div>
        <div style="font-size:12px;color:#a0aec0;margin-top:4px;">{order_date}</div>
      </td>
    </tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#16213e;" class="no-print">
    <tr><td style="padding:12px 30px;">
      <span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase;background:#0f3460;color:#90cdf4;margin-right:8px;">Payment: {order.payment_status or 'N/A'}</span>
      <span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase;background:#1a3a1a;color:#68d391;margin-right:8px;">Order: {order.order_status or 'N/A'}</span>
      <span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase;background:#3a1a1a;color:#fc8181;">Gateway: {gateway or 'N/A'}</span>
    </td></tr>
  </table>

  <div style="padding:28px 30px;">
    <div style="font-size:16px;font-weight:700;color:#1a1a2e;border-bottom:3px solid #667eea;padding-bottom:8px;margin-bottom:20px;">&#128230; Order Items</div>
    {shop_sections}

    <div style="font-size:16px;font-weight:700;color:#1a1a2e;border-bottom:3px solid #667eea;padding-bottom:8px;margin:28px 0 16px;">&#128181; Order Summary</div>
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;">
      {summary_rows}
    </table>
    {wallet_html}

    <div style="font-size:16px;font-weight:700;color:#1a1a2e;border-bottom:3px solid #667eea;padding-bottom:8px;margin:28px 0 16px;">&#128100; Customer &amp; Delivery</div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;"><tr>
      <td style="padding:16px;background:#f7fafc;border-right:1px solid #e2e8f0;width:50%;vertical-align:top;">
        <div style="font-size:11px;font-weight:700;color:#667eea;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;">&#128100; Customer Info</div>
        <div style="font-size:15px;font-weight:700;color:#1a202c;margin-bottom:6px;">{customer_name}</div>
        <div style="font-size:13px;color:#4a5568;margin-bottom:4px;">&#128222; {customer_contact}</div>
        <div style="font-size:13px;color:#4a5568;">&#9993; {customer_email}</div>
      </td>
      <td style="padding:16px;background:#fff;width:50%;vertical-align:top;">
        <div style="font-size:11px;font-weight:700;color:#667eea;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;">&#128205; Shipping Address</div>
        <div style="font-size:13px;color:#4a5568;">{shipping_addr}</div>
        {billing_html}
      </td>
    </tr></table>

    <div style="text-align:center;padding:24px 0 8px;" class="no-print">
      <a href="{dashboard_link}" style="display:inline-block;padding:12px 28px;background:#fff;color:#667eea;text-decoration:none;border-radius:6px;font-weight:700;font-size:14px;border:2px solid #667eea;margin:4px;">View in Dashboard</a>
      <a href="{print_link}" style="display:inline-block;padding:12px 28px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;text-decoration:none;border-radius:6px;font-weight:700;font-size:14px;margin:4px;">&#128438; Print Invoice</a>
    </div>
  </div>

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#1a1a2e;">
    <tr><td style="padding:22px 30px;text-align:center;color:#a0aec0;font-size:12px;">
      <p><strong style="color:#fff;">CTSPK Store</strong> &mdash; Admin Order Invoice</p>
      <p style="margin-top:8px;"><a href="{dashboard_link}" style="color:#667eea;text-decoration:none;">Dashboard</a></p>
      <p style="margin-top:10px;font-size:11px;">&#169; {year} CTSPK Store. All rights reserved.</p>
    </td></tr>
  </table>
</div>
</body>
</html>"""

    # ─── Public send methods ────────────────────────────────────────────────

    def send_shop_owner_email(self, session: Session, order: Order, shop_id: int) -> bool:
        """Send invoice email to the owner of a specific shop."""
        try:
            shop = session.get(Shop, shop_id)
            if not shop:
                return False
            owner = session.get(User, shop.owner_id)
            if not owner or not owner.email:
                return False

            shop_products = [op for op in order.order_products if op.shop_id == shop_id]
            if not shop_products:
                return False

            customer_name, customer_email, customer_contact = self._resolve_customer(session, order)
            shipping_addr = self._format_address(order.shipping_address)

            html = self._build_shop_owner_html(
                order, shop, shop_products,
                customer_name, customer_email, customer_contact, shipping_addr
            )
            subject = f"New Order #{order.tracking_number} — {shop.name}"
            plain = (
                f"Hello {shop.name},\n\nYou have a new order #{order.tracking_number}.\n"
                f"Customer: {customer_name}\nView: {self._base_url()}/dashboard/orders/{order.id}"
            )

            ok = self.email_helper._send_email_sync(
                to_email=owner.email, subject=subject,
                html_content=html, plain_text_content=plain
            )
            if ok:
                print(f"[order-email] shop-owner email sent to {owner.email} (shop #{shop_id})")
            return ok
        except Exception as e:
            print(f"[order-email] error sending shop-owner email: {e}")
            return False

    def send_order_emails_to_all_shops(self, session: Session, order: Order) -> Dict[int, bool]:
        """Send shop-owner emails for every shop in the order."""
        shop_ids = list({op.shop_id for op in order.order_products if op.shop_id})
        return {sid: self.send_shop_owner_email(session, order, sid) for sid in shop_ids}

    def send_admin_email(self, session: Session, order: Order) -> bool:
        """Send full-order invoice email to all root/admin users."""
        try:
            admins = session.exec(select(User).where(User.is_root == True)).all()
            if not admins:
                print("[order-email] no admin users found, skipping admin email")
                return False

            # Build shop groups
            shop_map: Dict[int, list] = {}
            for p in order.order_products:
                sid = p.shop_id or 0
                shop_map.setdefault(sid, []).append(p)

            shop_groups = []
            for sid, prods in shop_map.items():
                shop_name = f"Shop #{sid}"
                if sid:
                    shop = session.get(Shop, sid)
                    if shop:
                        shop_name = shop.name
                sub = sum(float(p.subtotal or 0) for p in prods)
                shop_groups.append((shop_name, prods, sub))

            customer_name, customer_email, customer_contact = self._resolve_customer(session, order)
            shipping_addr = self._format_address(order.shipping_address)
            billing_addr = self._format_address(order.billing_address)

            html = self._build_admin_html(
                order, shop_groups,
                customer_name, customer_email, customer_contact,
                shipping_addr, billing_addr
            )
            subject = f"[Admin] New Order #{order.tracking_number} — Full Invoice"
            total = float(order.paid_total or order.total or order.amount or 0)
            plain = (
                f"[Admin] New order #{order.tracking_number}\n"
                f"Customer: {customer_name}\nTotal: Rs.{total:,.2f}\n"
                f"Status: {order.order_status} | Payment: {order.payment_status}\n"
                f"View: {self._base_url()}/dashboard/orders/{order.id}"
            )

            any_ok = False
            for admin in admins:
                if not admin.email:
                    continue
                ok = self.email_helper._send_email_sync(
                    to_email=admin.email, subject=subject,
                    html_content=html, plain_text_content=plain
                )
                if ok:
                    print(f"[order-email] admin email sent to {admin.email}")
                    any_ok = True
            return any_ok
        except Exception as e:
            print(f"[order-email] error sending admin email: {e}")
            return False

    # ─── Legacy alias (kept for backward compatibility) ────────────────────

    def send_order_email_to_shop_owner(
        self, session: Session, order: Order, shop_id: int
    ) -> bool:
        return self.send_shop_owner_email(session, order, shop_id)


# Global instance
order_email_service = OrderEmailService()
