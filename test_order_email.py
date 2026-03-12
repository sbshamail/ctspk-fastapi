"""
test_order_email.py  — sends a test shop-owner email and admin email
for a real order to rurazza@gmail.com using the FastAPI email service.

Run from the project root:
    python test_order_email.py [--order-id 93] [--to rurazza@gmail.com]
"""

import sys
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import Session, select
from src.lib.db_con import engine
from src.api.models.order_model.orderModel import Order, OrderProduct
from src.api.models.shop_model.shopsModel import Shop
from src.api.models.usersModel import User
from src.api.core.email_helper import EmailHelper


def format_address(addr) -> str:
    if not addr:
        return "Not provided"
    if isinstance(addr, str):
        return addr
    if isinstance(addr, dict):
        keys = ["street", "street_address", "address", "city", "state", "zip", "zip_code", "country"]
        parts = [str(addr[k]) for k in keys if addr.get(k)]
        return ", ".join(parts) if parts else "Not provided"
    return str(addr)


def generate_product_html(products) -> str:
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

        row_bg = "#ffffff" if i % 2 == 0 else "#f8f9fa"
        variation_cell = (
            f'<br><span style="font-size:11px;color:#667eea;font-style:italic;">{variation}</span>'
            if variation else ""
        )
        sale_badge = ""
        if p.sale_price and float(p.sale_price) < unit_price:
            sale_badge = f'<br><span style="font-size:11px;color:#dc3545;text-decoration:line-through;">Rs.{unit_price:.2f}</span>'
            unit_price = float(p.sale_price)

        rows += f"""
<tr style="background:{row_bg};">
  <td style="padding:10px 8px;border-bottom:1px solid #e9ecef;vertical-align:middle;">
    <table cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="vertical-align:middle;padding-right:10px;">
        <img src="{img}" alt="{name}" width="60" height="60" style="border-radius:6px;object-fit:cover;border:1px solid #e2e8f0;display:block;" />
      </td>
      <td style="vertical-align:middle;">
        <div style="font-weight:600;color:#1a202c;font-size:14px;">{name}</div>
        <div style="font-size:12px;color:#718096;margin-top:3px;">SKU: {sku}</div>
        {variation_cell}
      </td>
    </tr></table>
  </td>
  <td style="padding:10px 8px;border-bottom:1px solid #e9ecef;text-align:center;font-size:13px;color:#4a5568;vertical-align:middle;"><strong>{p.order_quantity}</strong></td>
  <td style="padding:10px 8px;border-bottom:1px solid #e9ecef;text-align:right;font-size:13px;color:#4a5568;vertical-align:middle;">Rs.{unit_price:.2f}{sale_badge}</td>
  <td style="padding:10px 8px;border-bottom:1px solid #e9ecef;text-align:right;font-weight:700;font-size:14px;color:#667eea;vertical-align:middle;">Rs.{subtotal:.2f}</td>
</tr>"""
    return rows


def _wallet_html(total: float, wallet_amount_used: float, gateway: str) -> str:
    """Returns wallet payment breakdown HTML if wallet was used."""
    if not wallet_amount_used or wallet_amount_used <= 0:
        return ""
    gw = gateway.replace("_", " ") if gateway else "Other"
    remainder = total - wallet_amount_used
    remainder_row = ""
    if remainder > 0.005:
        remainder_row = (
            f"<tr><td style='font-size:14px;color:#4a5568;padding:4px 0;'>Paid via {gw}</td>"
            f"<td style='font-size:14px;font-weight:700;color:#4a5568;text-align:right;padding:4px 0;'>Rs.{remainder:.2f}</td></tr>"
        )
    return (
        f'<div style="margin-top:16px;background:#f0fff4;border:1px solid #9ae6b4;border-radius:8px;padding:16px 20px;">'
        f'<div style="font-size:13px;font-weight:700;color:#276749;margin-bottom:10px;">&#128179; Payment Breakdown</div>'
        f'<table width="100%" cellpadding="0" cellspacing="0">'
        f"<tr><td style='font-size:14px;color:#4a5568;padding:4px 0;'>Paid via Wallet</td>"
        f"<td style='font-size:14px;font-weight:700;color:#38a169;text-align:right;padding:4px 0;'>Rs.{wallet_amount_used:.2f}</td></tr>"
        f"{remainder_row}"
        f"</table></div>"
    )


def build_shop_owner_html(order, shop, shop_products, customer_name, customer_email,
                           customer_contact, shipping_addr) -> str:
    subtotal = sum(float(p.subtotal or 0) for p in shop_products)
    discount = sum(float(p.item_discount or 0) for p in shop_products)
    tax = sum(float(p.item_tax or 0) for p in shop_products)
    total = subtotal - discount + tax
    rows = generate_product_html(shop_products)
    order_date = order.created_at.strftime("%B %d, %Y %I:%M %p") if order.created_at else "N/A"
    dashboard_link = f"{os.getenv('DOMAIN', 'https:/shop.ghertak.com')}/dashboard/orders/{order.id}"
    print_link = f"{os.getenv('DOMAIN', 'https://shop.ghertak.com')}/dashboard/orders/{order.id}/invoice"
    year = datetime.now().year

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
@media print{{
  body{{background:#fff}}.wrap{{max-width:100%}}.no-print{{display:none!important}}
  .prod-table,tfoot,thead{{page-break-inside:avoid}}
}}
</style>
</head>
<body>
<div class="wrap">
  <!-- Invoice Header -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#1a1a2e;">
    <tr>
      <td style="padding:28px 30px;vertical-align:middle;">
        <div style="font-size:22px;font-weight:800;letter-spacing:1px;color:#fff;">CTSPK<span style="color:#667eea;">STORE</span></div>
        <div style="font-size:11px;color:#a0aec0;margin-top:4px;text-transform:uppercase;letter-spacing:1px;">Shop Order Invoice</div>
      </td>
      <td style="padding:28px 30px;text-align:right;vertical-align:middle;">
        <div style="display:inline-block;background:#667eea;color:#fff;font-size:11px;font-weight:700;padding:3px 14px;border-radius:20px;margin-bottom:6px;">INVOICE</div>
        <div style="font-size:18px;font-weight:700;color:#fff;">#{order.tracking_number}</div>
        <div style="font-size:12px;color:#a0aec0;margin-top:4px;">{order_date}</div>
      </td>
    </tr>
  </table>

  <!-- Shop Banner -->
  <div style="background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:14px 30px;">
    <div style="font-size:13px;opacity:.85;margin-bottom:2px;">Order for shop:</div>
    <div style="font-size:20px;font-weight:700;">{shop.name}</div>
  </div>

  <!-- Status Row -->
  <div style="background:#16213e;padding:10px 30px;" class="no-print">
    <span style="display:inline-block;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:600;text-transform:uppercase;background:#0f3460;color:#90cdf4;margin-right:8px;">Payment: {order.payment_status or "Pending"}</span>
    <span style="display:inline-block;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:600;text-transform:uppercase;background:#1a3a1a;color:#68d391;">Order: {order.order_status or "Pending"}</span>
  </div>

  <!-- Content -->
  <div style="padding:28px 30px;">
    <div style="font-size:15px;font-weight:700;color:#1a1a2e;border-bottom:2px solid #667eea;padding-bottom:8px;margin-bottom:14px;">&#128230; Products in this Order</div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;font-size:13px;">
      <thead>
        <tr style="background:#667eea;">
          <th style="padding:10px 12px;text-align:left;color:#fff;font-size:11px;text-transform:uppercase;letter-spacing:.5px;width:55%;">Product</th>
          <th style="padding:10px 12px;text-align:center;color:#fff;font-size:11px;text-transform:uppercase;letter-spacing:.5px;width:10%;">Qty</th>
          <th style="padding:10px 12px;text-align:right;color:#fff;font-size:11px;text-transform:uppercase;letter-spacing:.5px;width:17%;">Unit Price</th>
          <th style="padding:10px 12px;text-align:right;color:#fff;font-size:11px;text-transform:uppercase;letter-spacing:.5px;width:18%;">Total</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>

    <!-- Totals -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:18px;font-size:14px;">
      <tr><td style="padding:7px 0;color:#718096;">Subtotal</td><td style="padding:7px 0;text-align:right;font-weight:600;">Rs.{subtotal:.2f}</td></tr>
      {"<tr><td style='padding:7px 0;color:#38a169;'>Discount</td><td style='padding:7px 0;text-align:right;font-weight:600;color:#38a169;'>-Rs."+f"{discount:.2f}</td></tr>" if discount > 0 else ""}
      {"<tr><td style='padding:7px 0;color:#718096;'>Tax</td><td style='padding:7px 0;text-align:right;font-weight:600;'>Rs."+f"{tax:.2f}</td></tr>" if tax > 0 else ""}
      <tr style="border-top:2px solid #667eea;">
        <td style="padding-top:12px;font-size:18px;font-weight:800;color:#1a1a2e;">Your Total</td>
        <td style="padding-top:12px;text-align:right;font-size:18px;font-weight:800;color:#667eea;">Rs.{total:.2f}</td>
      </tr>
    </table>

    <!-- Customer -->
    <div style="font-size:15px;font-weight:700;color:#1a1a2e;border-bottom:2px solid #667eea;padding-bottom:8px;margin:24px 0 14px;">&#128100; Customer &amp; Delivery</div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;"><tr>
      <td style="padding:16px;background:#f7fafc;border-right:1px solid #e2e8f0;width:50%;vertical-align:top;">
        <div style="font-size:11px;font-weight:700;color:#667eea;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;">&#128100; Customer</div>
        <div style="font-size:15px;font-weight:700;color:#1a202c;margin-bottom:6px;">{customer_name}</div>
        <div style="font-size:13px;color:#4a5568;margin-bottom:4px;">&#128222; {customer_contact}</div>
        <div style="font-size:13px;color:#4a5568;">&#9993; {customer_email}</div>
      </td>
      <td style="padding:16px;background:#fff;width:50%;vertical-align:top;">
        <div style="font-size:11px;font-weight:700;color:#667eea;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;">&#128205; Shipping Address</div>
        <div style="font-size:13px;color:#4a5568;">{shipping_addr}</div>
      </td>
    </tr></table>

    <!-- Alert -->
    <div style="background:#fffbeb;border:1px solid #f6ad55;border-radius:6px;padding:12px 16px;font-size:13px;color:#744210;margin-top:20px;">
      <strong>&#9888; Important:</strong> Please process this order within 24 hours.
    </div>

    <!-- Buttons -->
    <div style="text-align:center;padding:20px 0;" class="no-print">
      <a href="{dashboard_link}" style="display:inline-block;padding:11px 28px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;text-decoration:none;border-radius:6px;font-weight:700;font-size:14px;margin:4px;">View Order in Dashboard</a>
      <a href="{print_link}" style="display:inline-block;padding:11px 28px;background:#fff;color:#667eea;text-decoration:none;border-radius:6px;font-weight:700;font-size:14px;border:2px solid #667eea;margin:4px;">&#128438; Print Invoice</a>
    </div>
  </div>

  <!-- Footer -->
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


def build_admin_html(order, shop_groups, customer_name, customer_email,
                      customer_contact, shipping_addr, billing_addr) -> str:
    # Subtotal = sum of all product subtotals (unit_price × qty)
    all_products = [p for _, prods, _ in shop_groups for p in prods]
    subtotal = sum(float(p.subtotal or 0) for p in all_products)
    # Grand total: prefer paid_total → total → amount (matches frontend)
    total = float(order.amount or 0)
    if hasattr(order, 'total') and order.total:
        total = float(order.total)
    if hasattr(order, 'paid_total') and order.paid_total:
        total = float(order.paid_total)
    sales_tax = float(order.sales_tax or 0) if hasattr(order, 'sales_tax') else 0
    discount = float(order.discount or 0) if hasattr(order, 'discount') else 0
    coupon_discount = float(order.coupon_discount or 0) if hasattr(order, 'coupon_discount') else 0
    delivery_fee = float(order.delivery_fee or 0) if hasattr(order, 'delivery_fee') else 0
    wallet_amount_used = float(order.wallet_amount_used or 0) if hasattr(order, 'wallet_amount_used') else 0
    order_date = order.created_at.strftime("%B %d, %Y %I:%M %p") if order.created_at else "N/A"
    gateway = str(order.payment_gateway or "N/A")
    dashboard_link = f"{os.getenv('DOMAIN', 'https://shop.ghertak.com')}/dashboard/orders/{order.id}"
    print_link = f"{os.getenv('DOMAIN', 'https://shop.ghertak.com')}/dashboard/orders/{order.id}/invoice"
    year = datetime.now().year

    # Per-shop sections
    shop_sections = ""
    for group_name, products, sub in shop_groups:
        rows = generate_product_html(products)
        shop_sections += f"""
<div style="margin-bottom:24px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="border-radius:8px;overflow:hidden;border:1px solid #e2e8f0;">
    <thead>
      <tr style="background:#667eea;">
        <td colspan="4" style="padding:10px 14px;color:#fff;font-weight:700;font-size:14px;">
          &#127978; {group_name} &nbsp;&mdash;&nbsp; <span style="font-weight:400;font-size:13px;">Subtotal: Rs.{sub:.2f}</span>
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
        <td style="padding:10px 14px;text-align:right;font-size:14px;font-weight:800;color:#667eea;">Rs.{sub:.2f}</td>
      </tr>
    </tfoot>
  </table>
</div>"""

    billing_html = ""
    if billing_addr and billing_addr != "Not provided":
        billing_html = f'<div style="margin-top:12px;"><div style="font-size:11px;font-weight:700;color:#667eea;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">&#128196; Billing Address</div><div style="font-size:13px;color:#4a5568;">{billing_addr}</div></div>'

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
  body{{background:#fff}}.wrap{{max-width:100%}}.no-print{{display:none!important}}
  thead,tfoot{{page-break-inside:avoid}}
}}
</style>
</head>
<body>
<div class="wrap">
  <!-- Header -->
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

  <!-- Status Badges -->
  <div style="background:#16213e;padding:12px 30px;" class="no-print">
    <span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase;background:#0f3460;color:#90cdf4;margin-right:8px;">Payment: {order.payment_status or "N/A"}</span>
    <span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase;background:#1a3a1a;color:#68d391;margin-right:8px;">Order: {order.order_status or "N/A"}</span>
    <span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase;background:#3a1a1a;color:#fc8181;">Gateway: {gateway}</span>
  </div>

  <!-- Content -->
  <div style="padding:28px 30px;">
    <div style="font-size:16px;font-weight:700;color:#1a1a2e;border-bottom:3px solid #667eea;padding-bottom:8px;margin-bottom:20px;">&#128230; Order Items</div>
    {shop_sections}

    <!-- Summary -->
    <div style="font-size:16px;font-weight:700;color:#1a1a2e;border-bottom:3px solid #667eea;padding-bottom:8px;margin:28px 0 16px;">&#128181; Order Summary</div>
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;">
      <tr><td style="padding:10px 20px;font-size:14px;color:#4a5568;border-bottom:1px solid #e2e8f0;">Subtotal</td><td style="padding:10px 20px;font-size:14px;text-align:right;color:#4a5568;border-bottom:1px solid #e2e8f0;">Rs.{subtotal:.2f}</td></tr>
      {"<tr><td style='padding:10px 20px;font-size:14px;color:#38a169;border-bottom:1px solid #e2e8f0;'>Discount</td><td style='padding:10px 20px;font-size:14px;text-align:right;color:#38a169;border-bottom:1px solid #e2e8f0;'>-Rs."+f"{discount:.2f}</td></tr>" if discount > 0 else ""}
      {"<tr><td style='padding:10px 20px;font-size:14px;color:#38a169;border-bottom:1px solid #e2e8f0;'>Coupon Discount</td><td style='padding:10px 20px;font-size:14px;text-align:right;color:#38a169;border-bottom:1px solid #e2e8f0;'>-Rs."+f"{coupon_discount:.2f}</td></tr>" if coupon_discount > 0 else ""}
      {"<tr><td style='padding:10px 20px;font-size:14px;color:#4a5568;border-bottom:1px solid #e2e8f0;'>Shipping Fee</td><td style='padding:10px 20px;font-size:14px;text-align:right;color:#4a5568;border-bottom:1px solid #e2e8f0;'>Rs."+f"{delivery_fee:.2f}</td></tr>" if delivery_fee > 0 else ""}
      {"<tr><td style='padding:10px 20px;font-size:14px;color:#4a5568;border-bottom:1px solid #e2e8f0;'>Tax</td><td style='padding:10px 20px;font-size:14px;text-align:right;color:#4a5568;border-bottom:1px solid #e2e8f0;'>Rs."+f"{sales_tax:.2f}</td></tr>" if sales_tax > 0 else ""}
      <tr><td style="padding:16px 20px;font-size:20px;font-weight:800;color:#1a1a2e;border-top:3px solid #667eea;">Grand Total</td><td style="padding:16px 20px;font-size:22px;font-weight:800;text-align:right;color:#667eea;border-top:3px solid #667eea;">Rs.{total:.2f}</td></tr>
    </table>
    {_wallet_html(total, wallet_amount_used, str(order.payment_gateway or ""))}


    <!-- Customer & Delivery -->
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

    <!-- Buttons -->
    <div style="text-align:center;padding:24px 0 8px;" class="no-print">
      <a href="{dashboard_link}" style="display:inline-block;padding:12px 28px;background:#fff;color:#667eea;text-decoration:none;border-radius:6px;font-weight:700;font-size:14px;border:2px solid #667eea;margin:4px;">View in Dashboard</a>
      <a href="{print_link}" style="display:inline-block;padding:12px 28px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;text-decoration:none;border-radius:6px;font-weight:700;font-size:14px;margin:4px;">&#128438; Print Invoice</a>
    </div>
  </div>

  <!-- Footer -->
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", default="rurazza@gmail.com")
    parser.add_argument("--order-id", type=int, default=0)
    args = parser.parse_args()

    helper = EmailHelper()

    with Session(engine) as session:
        # Find order
        if args.order_id:
            order = session.get(Order, args.order_id)
            if not order:
                print(f"Order {args.order_id} not found")
                return
        else:
            order = session.exec(select(Order).order_by(Order.created_at.desc())).first()
            if not order:
                print("No orders found")
                return

        print(f"Using order #{order.tracking_number} (ID={order.id})")

        # Customer info
        customer_name = order.customer_name or "Guest"
        customer_contact = order.customer_contact or "Not provided"
        customer_email = "Not provided"
        if order.customer_id:
            user = session.get(User, order.customer_id)
            if user:
                customer_email = user.email
                if not order.customer_name:
                    customer_name = user.name

        shipping_addr = format_address(order.shipping_address)
        billing_addr = format_address(order.billing_address)

        # Get order products
        products = session.exec(
            select(OrderProduct).where(OrderProduct.order_id == order.id)
        ).all()

        # ── Shop-owner email ──────────────────────────────────────────────────
        shop_ids = list({p.shop_id for p in products if p.shop_id})
        if not shop_ids:
            print("No shop-linked products found")
            return

        for shop_id in shop_ids:
            shop = session.get(Shop, shop_id)
            if not shop:
                continue

            shop_products = [p for p in products if p.shop_id == shop_id]
            html = build_shop_owner_html(
                order, shop, shop_products,
                customer_name, customer_email, customer_contact, shipping_addr
            )
            subject = f"[TEST] Shop Invoice — Order #{order.tracking_number} ({shop.name})"
            plain = f"[TEST] Shop owner email for order #{order.tracking_number}\nShop: {shop.name}"

            print(f"Sending shop-owner email to {args.to} (shop: {shop.name}) ...")
            ok = helper._send_email_sync(to_email=args.to, subject=subject,
                                          html_content=html, plain_text_content=plain)
            print(f"  {'[OK] Sent' if ok else '[FAIL] Failed'}")

        # ── Admin email ───────────────────────────────────────────────────────
        shop_groups = []
        for shop_id in shop_ids:
            shop = session.get(Shop, shop_id)
            shop_name = shop.name if shop else f"Shop #{shop_id}"
            shop_prods = [p for p in products if p.shop_id == shop_id]
            sub = sum(float(p.subtotal or 0) for p in shop_prods)
            shop_groups.append((shop_name, shop_prods, sub))

        html = build_admin_html(
            order, shop_groups,
            customer_name, customer_email, customer_contact,
            shipping_addr, billing_addr
        )
        subject = f"[TEST][Admin] Full Invoice — Order #{order.tracking_number}"
        plain = f"[TEST] Admin invoice for order #{order.tracking_number}\nTotal: Rs.{float(order.amount or 0):.2f}"

        print(f"Sending admin email to {args.to} ...")
        ok = helper._send_email_sync(to_email=args.to, subject=subject,
                                      html_content=html, plain_text_content=plain)
        print(f"  {'[OK] Sent' if ok else '[FAIL] Failed'}")


if __name__ == "__main__":
    main()
