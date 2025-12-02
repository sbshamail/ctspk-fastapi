# src/api/services/order_email_service.py
"""
Service for sending order notification emails to shop owners
"""
from typing import List, Dict, Any
from sqlmodel import Session, select
from datetime import datetime
from pathlib import Path

from src.api.models.order_model.orderModel import Order, OrderProduct
from src.api.models.shop_model.shopsModel import Shop
from src.api.models.usersModel import User
from src.api.core.email_helper import EmailHelper


class OrderEmailService:
    """Service to send order emails to shop owners"""

    def __init__(self):
        self.email_helper = EmailHelper()
        self.template_path = Path(__file__).parent.parent / "templates" / "order_email_template.html"

    def _load_email_template(self) -> str:
        """Load email template from file"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading email template: {e}")
            return ""

    def _generate_product_html(self, products: List[OrderProduct]) -> str:
        """Generate HTML for product list"""
        products_html = ""

        for product in products:
            # Get product image (use first image or default)
            product_image = "https://via.placeholder.com/100"
            if product.product_snapshot and isinstance(product.product_snapshot, dict):
                image_data = product.product_snapshot.get('image')
                if image_data:
                    if isinstance(image_data, dict):
                        product_image = image_data.get('thumbnail') or image_data.get('original') or product_image
                    elif isinstance(image_data, str):
                        product_image = image_data

            # Get product name
            product_name = "Unknown Product"
            if product.product_snapshot and isinstance(product.product_snapshot, dict):
                product_name = product.product_snapshot.get('name', product_name)

            # Get variation details if exists
            variation_info = ""
            if product.variation_data and isinstance(product.variation_data, dict):
                variation_info = f"<div class='product-meta'>Variation: {product.variation_data.get('title', 'N/A')}</div>"

            # Get SKU
            sku = "N/A"
            if product.product_snapshot and isinstance(product.product_snapshot, dict):
                sku = product.product_snapshot.get('sku', 'N/A')

            # Calculate item total
            item_total = float(product.subtotal or 0)
            unit_price = float(product.unit_price or 0)
            sale_price = float(product.sale_price) if product.sale_price else None

            # Build product HTML
            product_html = f"""
            <div class="product-item">
                <img src="{product_image}" alt="{product_name}" class="product-image" />
                <div class="product-details">
                    <div class="product-name">{product_name}</div>
                    <div class="product-meta">SKU: {sku}</div>
                    <div class="product-meta">Quantity: {product.order_quantity}</div>
                    {variation_info}
                    <div class="product-meta">
                        Unit Price: ${unit_price:.2f}
                        {f' <span style="color: #dc3545;">(Sale: ${sale_price:.2f})</span>' if sale_price else ''}
                    </div>
                    <div class="product-price">Total: ${item_total:.2f}</div>
                </div>
            </div>
            """
            products_html += product_html

        return products_html

    def _format_address(self, address_data: Any) -> str:
        """Format address from various formats"""
        if not address_data:
            return "No address provided"

        if isinstance(address_data, str):
            return address_data

        if isinstance(address_data, dict):
            parts = []
            for key in ['street', 'street_address', 'address', 'city', 'state', 'zip', 'zip_code', 'country']:
                if key in address_data and address_data[key]:
                    parts.append(str(address_data[key]))
            return ", ".join(parts) if parts else "Address not available"

        return str(address_data)

    def prepare_shop_order_email(
        self,
        session: Session,
        order: Order,
        shop_id: int
    ) -> Dict[str, Any]:
        """
        Prepare email data for a specific shop's products in the order

        Returns dict with 'success', 'shop_owner_email', 'subject', 'html_content'
        """
        try:
            # Get shop
            shop = session.get(Shop, shop_id)
            if not shop:
                return {"success": False, "error": "Shop not found"}

            # Get shop owner
            shop_owner = session.get(User, shop.owner_id)
            if not shop_owner or not shop_owner.email:
                return {"success": False, "error": "Shop owner email not found"}

            # Get order products for this shop only
            shop_products = [op for op in order.order_products if op.shop_id == shop_id]

            if not shop_products:
                return {"success": False, "error": "No products for this shop"}

            # Calculate shop-specific totals
            shop_subtotal = sum(float(op.subtotal or 0) for op in shop_products)
            shop_tax = sum(float(op.item_tax or 0) for op in shop_products)
            shop_discount = sum(float(op.item_discount or 0) for op in shop_products)
            shop_total = shop_subtotal + shop_tax - shop_discount

            # Generate products HTML
            products_html = self._generate_product_html(shop_products)

            # Get customer info
            customer = session.get(User, order.customer_id) if order.customer_id else None
            customer_name = customer.name if customer else order.customer_name or "Guest"
            customer_email = customer.email if customer else "Not provided"
            customer_contact = order.customer_contact or "Not provided"

            # Format shipping address
            shipping_address = self._format_address(order.shipping_address)

            # Load template
            template = self._load_email_template()
            if not template:
                return {"success": False, "error": "Email template not found"}

            # Prepare replacements
            replacements = {
                'order_tracking_number': order.tracking_number,
                'order_date': order.created_at.strftime("%B %d, %Y %I:%M %p") if order.created_at else "N/A",
                'payment_status': order.payment_status or "Pending",
                'order_status': order.order_status or "Pending",
                'shop_name': shop.name,
                'products_html': products_html,
                'shop_subtotal': f"{shop_subtotal:.2f}",
                'shop_tax': f"{shop_tax:.2f}",
                'shop_discount': f"{shop_discount:.2f}",
                'shop_total': f"{shop_total:.2f}",
                'customer_name': customer_name,
                'customer_contact': customer_contact,
                'customer_email': customer_email,
                'shipping_address': shipping_address,
                'dashboard_link': f"{self._get_base_url()}/dashboard/orders/{order.id}",
                'support_link': f"{self._get_base_url()}/support",
                'privacy_link': f"{self._get_base_url()}/privacy",
                'site_name': self._get_site_name(),
                'current_year': datetime.now().year,
            }

            # Apply replacements
            html_content = template
            for key, value in replacements.items():
                html_content = html_content.replace(f"{{{{{key}}}}}", str(value))

            subject = f"New Order #{order.tracking_number} - {shop.name}"

            return {
                "success": True,
                "shop_owner_email": shop_owner.email,
                "shop_owner_name": shop_owner.name,
                "subject": subject,
                "html_content": html_content
            }

        except Exception as e:
            print(f"Error preparing shop order email: {e}")
            return {"success": False, "error": str(e)}

    def send_order_email_to_shop_owner(
        self,
        session: Session,
        order: Order,
        shop_id: int
    ) -> bool:
        """
        Send order notification email to a specific shop owner

        Args:
            session: Database session
            order: Order instance
            shop_id: Shop ID to send email for

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Prepare email
            email_data = self.prepare_shop_order_email(session, order, shop_id)

            if not email_data.get("success"):
                print(f"Failed to prepare email: {email_data.get('error')}")
                return False

            # Send email
            success = self.email_helper._send_email_sync(
                to_email=email_data["shop_owner_email"],
                subject=email_data["subject"],
                html_content=email_data["html_content"]
            )

            if success:
                print(f"✅ Order email sent to {email_data['shop_owner_email']} for shop {shop_id}")
            else:
                print(f"❌ Failed to send email to {email_data['shop_owner_email']}")

            return success

        except Exception as e:
            print(f"Error sending order email: {e}")
            return False

    def send_order_emails_to_all_shops(
        self,
        session: Session,
        order: Order
    ) -> Dict[int, bool]:
        """
        Send order notification emails to all shop owners in the order

        Args:
            session: Database session
            order: Order instance

        Returns:
            Dictionary mapping shop_id to success status
        """
        results = {}

        # Get unique shop IDs from order products
        shop_ids = list(set([op.shop_id for op in order.order_products if op.shop_id]))

        for shop_id in shop_ids:
            success = self.send_order_email_to_shop_owner(session, order, shop_id)
            results[shop_id] = success

        return results

    def _get_base_url(self) -> str:
        """Get base URL from environment or config"""
        import os
        return os.getenv('BASE_URL', 'http://localhost:3000')

    def _get_site_name(self) -> str:
        """Get site name from environment or config"""
        import os
        return os.getenv('SITE_NAME', 'Your Store')


# Create global instance
order_email_service = OrderEmailService()
