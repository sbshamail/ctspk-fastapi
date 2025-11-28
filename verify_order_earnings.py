"""
Verify Shop Earnings for a specific order
Usage: python verify_order_earnings.py <order_id>
Example: python verify_order_earnings.py 79
"""

import sys
from decimal import Decimal
from sqlmodel import Session, select
from src.lib.db_con import engine
from src.api.models.order_model.orderModel import Order, OrderProduct
from src.api.models.withdrawModel import ShopEarning
from src.api.models.shopModel import Shop


def verify_order_earnings(order_id: int):
    """Verify shop earnings for a specific order"""

    with Session(engine) as session:
        # 1. Get Order Details
        order = session.get(Order, order_id)
        if not order:
            print(f"❌ Order {order_id} not found!")
            return

        print("=" * 80)
        print(f"ORDER DETAILS - ID: {order_id}")
        print("=" * 80)
        print(f"Tracking Number: {order.tracking_number}")
        print(f"Order Status: {order.order_status}")
        print(f"Payment Status: {order.payment_status}")
        print(f"Total Amount: ${order.total_amount}")
        print(f"Delivery Fee: ${order.delivery_fee}")
        print(f"Discount: ${order.discount_amount}")
        print(f"Final Amount: ${order.final_amount}")
        print()

        # 2. Get Order Products
        order_products = session.exec(
            select(OrderProduct).where(OrderProduct.order_id == order_id)
        ).all()

        if not order_products:
            print(f"⚠️ No order products found for order {order_id}")
            return

        print("=" * 80)
        print(f"ORDER PRODUCTS ({len(order_products)} items)")
        print("=" * 80)

        total_subtotal = sum(op.subtotal for op in order_products)

        expected_earnings = []

        for i, op in enumerate(order_products, 1):
            shop = session.get(Shop, op.shop_id) if op.shop_id else None
            shop_name = shop.name if shop else "N/A"

            print(f"\n[{i}] Order Product ID: {op.id}")
            print(f"    Product ID: {op.product_id}")
            print(f"    Shop ID: {op.shop_id} ({shop_name})")
            print(f"    Quantity: {op.quantity}")
            print(f"    Price: ${op.price}")
            print(f"    Subtotal: ${op.subtotal}")
            print(f"    Admin Commission: ${op.admin_commission} ({op.admin_commission_percent}%)")

            # Calculate proportional delivery fee
            delivery_fee_per_product = Decimal("0.00")
            if order.delivery_fee and total_subtotal > 0:
                delivery_fee_per_product = Decimal(str(order.delivery_fee)) * (
                    Decimal(str(op.subtotal)) / Decimal(str(total_subtotal))
                )

            # Calculate expected shop earning
            expected_earning = (
                Decimal(str(op.subtotal))
                - op.admin_commission
                - delivery_fee_per_product
            )

            print(f"    Proportional Delivery Fee: ${delivery_fee_per_product:.2f}")
            print(f"    Expected Shop Earning: ${expected_earning:.2f}")

            expected_earnings.append({
                'order_product_id': op.id,
                'shop_id': op.shop_id,
                'shop_name': shop_name,
                'subtotal': op.subtotal,
                'admin_commission': op.admin_commission,
                'delivery_fee': delivery_fee_per_product,
                'expected_earning': expected_earning
            })

        # 3. Get Actual Shop Earnings from DB
        print("\n" + "=" * 80)
        print(f"ACTUAL SHOP EARNINGS IN DATABASE")
        print("=" * 80)

        shop_earnings = session.exec(
            select(ShopEarning).where(ShopEarning.order_id == order_id)
        ).all()

        if not shop_earnings:
            print(f"\n⚠️ NO SHOP EARNINGS FOUND FOR ORDER {order_id}!")
            print(f"   Expected {len([e for e in expected_earnings if e['shop_id']])} earning records")
            print(f"\n   💡 This order may need shop earnings to be created.")
            print(f"   💡 Make sure order status is COMPLETED and call the update endpoint.")
        else:
            print(f"\nFound {len(shop_earnings)} shop earning record(s):\n")

            for i, se in enumerate(shop_earnings, 1):
                shop = session.get(Shop, se.shop_id)
                shop_name = shop.name if shop else "Unknown"

                print(f"[{i}] Earning ID: {se.id}")
                print(f"    Shop: {se.shop_id} ({shop_name})")
                print(f"    Order Product ID: {se.order_product_id}")
                print(f"    Order Amount: ${se.order_amount}")
                print(f"    Admin Commission: ${se.admin_commission}")
                print(f"    Shop Earning: ${se.shop_earning}")
                print(f"    Is Settled: {se.is_settled}")
                print(f"    Created At: {se.created_at}")
                print()

        # 4. Comparison
        print("=" * 80)
        print(f"VERIFICATION: EXPECTED vs ACTUAL")
        print("=" * 80)
        print()

        all_correct = True
        missing_count = 0
        mismatch_count = 0

        for expected in expected_earnings:
            if not expected['shop_id']:
                print(f"⚠️ Order Product {expected['order_product_id']}: No shop_id, skipped")
                continue

            # Find matching actual earning
            actual = next(
                (se for se in shop_earnings if se.order_product_id == expected['order_product_id']),
                None
            )

            print(f"Order Product {expected['order_product_id']} | Shop: {expected['shop_name']}")
            print(f"  Expected Earning: ${expected['expected_earning']:.2f}")

            if actual:
                print(f"  Actual Earning:   ${actual.shop_earning:.2f}")

                # Compare with tolerance of $0.01
                diff = abs(expected['expected_earning'] - actual.shop_earning)
                if diff < Decimal("0.01"):
                    print(f"  ✅ CORRECT (diff: ${diff:.4f})")
                else:
                    print(f"  ⚠️ MISMATCH! Difference: ${diff:.2f}")
                    all_correct = False
                    mismatch_count += 1
            else:
                print(f"  ❌ MISSING - No earning record found in database!")
                all_correct = False
                missing_count += 1

            print()

        # 5. Summary
        print("=" * 80)
        print(f"SUMMARY")
        print("=" * 80)

        if all_correct:
            print(f"✅ All shop earnings are CORRECT!")
            print(f"   Total earning records: {len(shop_earnings)}")
            total_earnings = sum(se.shop_earning for se in shop_earnings)
            total_commission = sum(se.admin_commission for se in shop_earnings)
            print(f"   Total shop earnings: ${total_earnings:.2f}")
            print(f"   Total admin commission: ${total_commission:.2f}")
        else:
            print(f"⚠️ ISSUES FOUND:")
            if missing_count > 0:
                print(f"   - {missing_count} missing earning record(s)")
            if mismatch_count > 0:
                print(f"   - {mismatch_count} mismatch(es) in calculations")
            print(f"\n💡 Recommendation:")
            if missing_count > 0:
                print(f"   1. Ensure order status is COMPLETED")
                print(f"   2. Call PUT /order/update/{order_id} or PATCH /order/{order_id}/status")
                print(f"   3. The create_shop_earning function will run automatically")

        # 6. Check for duplicates
        print("\n" + "=" * 80)
        print(f"DUPLICATE CHECK")
        print("=" * 80)

        from collections import Counter
        product_ids = [se.order_product_id for se in shop_earnings]
        duplicates = [item for item, count in Counter(product_ids).items() if count > 1]

        if duplicates:
            print(f"❌ DUPLICATES FOUND for order_product_ids: {duplicates}")
            print(f"   This should not happen! Please investigate.")
        else:
            print(f"✅ No duplicates found")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_order_earnings.py <order_id>")
        print("Example: python verify_order_earnings.py 79")
        sys.exit(1)

    try:
        order_id = int(sys.argv[1])
        verify_order_earnings(order_id)
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid order ID")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
