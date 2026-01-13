"""
Backfill Shop Earnings for Completed Orders

This script creates ShopEarning records for all completed orders that don't have them.
This fixes the issue where available_balance shows negative because earnings weren't tracked.

Usage:
    python backfill_shop_earnings.py              # Dry run (preview only)
    python backfill_shop_earnings.py --execute    # Actually create records
    python backfill_shop_earnings.py --shop-id 3  # Only for specific shop
"""

import sys
import argparse
from decimal import Decimal
from datetime import datetime
from sqlmodel import Session, select, func
from src.lib.db_con import engine
from src.api.models.order_model.orderModel import Order, OrderProduct, OrderStatusEnum
from src.api.models.withdrawModel import ShopEarning
from src.api.models.shop_model.shopsModel import Shop


def get_completed_orders(session, shop_id: int = None):
    """Get all completed orders, optionally filtered by shop"""
    query = select(Order).where(Order.order_status == OrderStatusEnum.COMPLETED)

    if shop_id:
        # Get orders that have products from this shop
        subquery = select(OrderProduct.order_id).where(OrderProduct.shop_id == shop_id).distinct()
        query = query.where(Order.id.in_(subquery))

    return session.exec(query.order_by(Order.id)).all()


def get_orders_without_earnings(session, shop_id: int = None):
    """Get completed orders that don't have ShopEarning records"""
    # Get all order IDs that already have earnings
    orders_with_earnings = select(ShopEarning.order_id).distinct()

    query = select(Order).where(
        Order.order_status == OrderStatusEnum.COMPLETED,
        Order.id.notin_(orders_with_earnings)
    )

    if shop_id:
        subquery = select(OrderProduct.order_id).where(OrderProduct.shop_id == shop_id).distinct()
        query = query.where(Order.id.in_(subquery))

    return session.exec(query.order_by(Order.id)).all()


def calculate_shop_earning_for_product(order: Order, order_product: OrderProduct, order_products: list) -> Decimal:
    """Calculate shop earning for a specific order product"""
    # Calculate proportional delivery fee
    delivery_fee_per_product = Decimal("0.00")
    if order.delivery_fee and len(order_products) > 0:
        total_subtotal = sum(Decimal(str(op.subtotal)) for op in order_products)
        if total_subtotal > 0:
            delivery_fee_per_product = Decimal(str(order.delivery_fee)) * (
                Decimal(str(order_product.subtotal)) / total_subtotal
            )

    # Calculate shop earning
    shop_earning = (
        Decimal(str(order_product.subtotal))
        - order_product.admin_commission
        - delivery_fee_per_product
    )

    return shop_earning


def create_earnings_for_order(session, order: Order, dry_run: bool = True) -> list:
    """Create ShopEarning records for an order"""
    created_earnings = []

    # Get all order products for this order
    order_products = session.exec(
        select(OrderProduct).where(OrderProduct.order_id == order.id)
    ).all()

    if not order_products:
        return created_earnings

    for order_product in order_products:
        if not order_product.shop_id:
            continue

        # Check if earning already exists for this specific order product
        existing = session.exec(
            select(ShopEarning).where(
                ShopEarning.order_id == order.id,
                ShopEarning.order_product_id == order_product.id
            )
        ).first()

        if existing:
            continue

        # Calculate shop earning
        shop_earning = calculate_shop_earning_for_product(order, order_product, order_products)

        # Create earning record
        earning = ShopEarning(
            shop_id=order_product.shop_id,
            order_id=order.id,
            order_product_id=order_product.id,
            order_amount=Decimal(str(order_product.subtotal)),
            admin_commission=order_product.admin_commission,
            shop_earning=shop_earning,
            is_settled=False,
            settled_at=None
        )

        if not dry_run:
            session.add(earning)

        created_earnings.append({
            'order_id': order.id,
            'order_product_id': order_product.id,
            'shop_id': order_product.shop_id,
            'order_amount': order_product.subtotal,
            'admin_commission': order_product.admin_commission,
            'shop_earning': shop_earning
        })

    return created_earnings


def backfill_shop_earnings(dry_run: bool = True, shop_id: int = None):
    """Main backfill function"""
    print("=" * 80)
    print("SHOP EARNINGS BACKFILL SCRIPT")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'EXECUTE (creating records)'}")
    if shop_id:
        print(f"Filter: Shop ID {shop_id}")
    print(f"Started at: {datetime.now()}")
    print()

    with Session(engine) as session:
        # Get statistics
        total_completed = len(get_completed_orders(session, shop_id))
        orders_without_earnings = get_orders_without_earnings(session, shop_id)

        print(f"Total completed orders: {total_completed}")
        print(f"Orders without earnings: {len(orders_without_earnings)}")
        print()

        if not orders_without_earnings:
            print("No orders need backfilling. All completed orders have earnings records.")
            return

        # Process each order
        total_earnings_created = 0
        total_shop_earning_amount = Decimal("0.00")
        total_admin_commission = Decimal("0.00")
        shop_summaries = {}

        print("-" * 80)
        print("PROCESSING ORDERS")
        print("-" * 80)

        for order in orders_without_earnings:
            earnings = create_earnings_for_order(session, order, dry_run)

            if earnings:
                print(f"\nOrder #{order.id} (Tracking: {order.tracking_number})")
                print(f"  Order Date: {order.created_at}")
                print(f"  Creating {len(earnings)} earning record(s):")

                for e in earnings:
                    shop = session.get(Shop, e['shop_id'])
                    shop_name = shop.name if shop else "Unknown"

                    print(f"    - Shop: {shop_name} (ID: {e['shop_id']})")
                    print(f"      Order Amount: Rs.{e['order_amount']:.2f}")
                    print(f"      Admin Commission: Rs.{e['admin_commission']:.2f}")
                    print(f"      Shop Earning: Rs.{e['shop_earning']:.2f}")

                    total_earnings_created += 1
                    total_shop_earning_amount += e['shop_earning']
                    total_admin_commission += e['admin_commission']

                    # Track per-shop summary
                    if e['shop_id'] not in shop_summaries:
                        shop_summaries[e['shop_id']] = {
                            'name': shop_name,
                            'count': 0,
                            'total_earning': Decimal("0.00"),
                            'total_commission': Decimal("0.00")
                        }
                    shop_summaries[e['shop_id']]['count'] += 1
                    shop_summaries[e['shop_id']]['total_earning'] += e['shop_earning']
                    shop_summaries[e['shop_id']]['total_commission'] += e['admin_commission']

        # Commit if not dry run
        if not dry_run:
            session.commit()
            print("\n" + "=" * 80)
            print("CHANGES COMMITTED TO DATABASE")
            print("=" * 80)

        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"\nOrders processed: {len(orders_without_earnings)}")
        print(f"Earning records {'to create' if dry_run else 'created'}: {total_earnings_created}")
        print(f"Total shop earnings: Rs.{total_shop_earning_amount:.2f}")
        print(f"Total admin commission: Rs.{total_admin_commission:.2f}")

        if shop_summaries:
            print("\n" + "-" * 80)
            print("PER-SHOP BREAKDOWN")
            print("-" * 80)
            for shop_id, summary in shop_summaries.items():
                print(f"\n  Shop: {summary['name']} (ID: {shop_id})")
                print(f"    Earning records: {summary['count']}")
                print(f"    Total earnings: Rs.{summary['total_earning']:.2f}")
                print(f"    Total commission: Rs.{summary['total_commission']:.2f}")

        if dry_run:
            print("\n" + "=" * 80)
            print("THIS WAS A DRY RUN - NO CHANGES WERE MADE")
            print("Run with --execute to create the records")
            print("=" * 80)

        print(f"\nCompleted at: {datetime.now()}")


def show_current_status(shop_id: int = None):
    """Show current status of shop earnings"""
    print("=" * 80)
    print("CURRENT SHOP EARNINGS STATUS")
    print("=" * 80)

    with Session(engine) as session:
        # Get all shops
        query = select(Shop)
        if shop_id:
            query = query.where(Shop.id == shop_id)
        shops = session.exec(query).all()

        for shop in shops:
            # Count earnings
            earnings_count = session.exec(
                select(func.count(ShopEarning.id)).where(ShopEarning.shop_id == shop.id)
            ).one()

            # Sum earnings
            total_earnings = session.exec(
                select(func.coalesce(func.sum(ShopEarning.shop_earning), 0)).where(
                    ShopEarning.shop_id == shop.id,
                    ShopEarning.is_settled == False
                )
            ).one()

            # Count completed orders for this shop
            completed_orders = session.exec(
                select(func.count(OrderProduct.id.distinct())).where(
                    OrderProduct.shop_id == shop.id,
                    OrderProduct.order_id.in_(
                        select(Order.id).where(Order.order_status == OrderStatusEnum.COMPLETED)
                    )
                )
            ).one()

            print(f"\nShop: {shop.name} (ID: {shop.id})")
            print(f"  Total earning records: {earnings_count}")
            print(f"  Unsettled earnings: Rs.{total_earnings:.2f}")
            print(f"  Completed order products: {completed_orders}")

            if completed_orders > 0 and earnings_count == 0:
                print(f"  WARNING: Has completed orders but no earnings!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill ShopEarning records for completed orders"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually create records (default is dry run)"
    )
    parser.add_argument(
        "--shop-id",
        type=int,
        help="Only process orders for a specific shop"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current status without making changes"
    )

    args = parser.parse_args()

    try:
        if args.status:
            show_current_status(args.shop_id)
        else:
            backfill_shop_earnings(
                dry_run=not args.execute,
                shop_id=args.shop_id
            )
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
