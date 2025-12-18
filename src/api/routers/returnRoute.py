# src/api/routes/returnRoute.py
from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import select, func
from datetime import datetime, timedelta
from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listRecords, updateOp
from src.api.core.transaction_logger import TransactionLogger
from src.api.core.notification_helper import NotificationHelper
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)
from src.api.models.returnModel import (
    ReturnRequest, ReturnRequestCreate, ReturnRequestRead, ReturnRequestUpdate,
    ReturnItem, ReturnItemCreate, ReturnItemRead,
    ReturnStatus, ReturnType, RefundStatus,
    WalletTransaction, UserWallet
)
from src.api.models.transactionLogModel import TransactionLogCreate, TransactionType

router = APIRouter(prefix="/returns", tags=["Returns & Refunds"])


# ✅ CREATE RETURN REQUEST
@router.post("/request")
def create_return_request(
    request: ReturnRequestCreate,
    session: GetSession,
    user:requireSignin,
    background_tasks: BackgroundTasks = None,
):
    print("🔄 Creating return request:", request.model_dump())
    print ("User signin:",user)
    # Verify order exists and belongs to user
    from src.api.models.order_model.orderModel import Order, OrderProduct
    order = session.get(Order, request.order_id)
    raiseExceptions((order, 404, "Order not found"))
    print ("order detail:",order)
    if order.customer_id != user.get("id"):
        return api_response(403, "Not authorized to return this order")

    # Check if order is eligible for return
    if order.order_status not in ["order-completed", "order-out-for-delivery"]:
        return api_response(400, "Order is not eligible for return")

    # Check if return period has expired (e.g., 30 days)
    return_period_days = 30
    # Use order created_at as fallback if order_status_history is not available
    order_date = order.created_at
    if order.order_status_history and order.order_status_history.order_completed_date:
        order_date = order.order_status_history.order_completed_date
    if (datetime.utcnow() - order_date).days > return_period_days:
        return api_response(400, "Return period has expired")

    # ✅ CHECK IF PRODUCTS ARE ALREADY RETURNED
    if request.return_type == ReturnType.FULL_ORDER:
        # Check if any product in the order is already returned
        already_returned_items = []
        for order_item in order.order_products:
            if order_item.is_returned:
                already_returned_items.append({
                    "order_item_id": order_item.id,
                    "product_id": order_item.product_id,
                    "return_request_id": order_item.return_request_id
                })

        if already_returned_items:
            return api_response(
                400,
                "Some products in this order have already been returned",
                {"already_returned_items": already_returned_items}
            )

        # Check if there's an existing pending/approved return for this full order
        existing_return = session.execute(
            select(ReturnRequest).where(
                ReturnRequest.order_id == request.order_id,
                ReturnRequest.return_type == ReturnType.FULL_ORDER,
                ReturnRequest.status.in_([ReturnStatus.PENDING, ReturnStatus.APPROVED])
            )
        ).scalars().first()

        if existing_return:
            return api_response(
                400,
                f"A return request already exists for this order (Return #{existing_return.id})",
                {"existing_return_id": existing_return.id, "status": existing_return.status.value}
            )
    else:
        # SINGLE_PRODUCT - Check if specific products are already returned
        for item in request.items:
            order_item_check = session.execute(
                select(OrderProduct).where(OrderProduct.id == item.order_item_id)
            ).scalars().first()

            if order_item_check:
                # Check if already returned
                if order_item_check.is_returned:
                    return api_response(
                        400,
                        f"Product (order item #{item.order_item_id}) has already been returned",
                        {
                            "order_item_id": order_item_check.id,
                            "product_id": order_item_check.product_id,
                            "return_request_id": order_item_check.return_request_id,
                            "returned_quantity": order_item_check.returned_quantity
                        }
                    )

                # Check if there's a pending return for this item
                existing_return_item = session.execute(
                    select(ReturnItem).where(
                        ReturnItem.order_item_id == item.order_item_id
                    )
                ).scalars().first()

                if existing_return_item:
                    # Check if return request is still pending/approved
                    parent_return = session.get(ReturnRequest, existing_return_item.return_request_id)
                    if parent_return and parent_return.status in [ReturnStatus.PENDING, ReturnStatus.APPROVED]:
                        return api_response(
                            400,
                            f"A return request is already pending for order item #{item.order_item_id}",
                            {
                                "order_item_id": item.order_item_id,
                                "existing_return_id": parent_return.id,
                                "status": parent_return.status.value
                            }
                        )

    # Calculate refund amount based on return type
    refund_amount = 0.0

    if request.return_type == ReturnType.FULL_ORDER:
        refund_amount = order.total or 0.0
        return_items = []

        # Create return items for all order items
        for order_item in order.order_products:
            return_item = ReturnItem(
                order_item_id=order_item.id,
                product_id=order_item.product_id,
                variation_option_id=order_item.variation_option_id,
                quantity=int(float(order_item.order_quantity)) if order_item.order_quantity else 0,
                unit_price=order_item.unit_price,
                refund_amount=order_item.subtotal
            )
            return_items.append(return_item)
            refund_amount += order_item.subtotal
            
    else:  # SINGLE_PRODUCT
        return_items = []
        for item in request.items:
            order_item_stmt = select(OrderProduct).where(OrderProduct.id == item.order_item_id)
            order_item = session.execute(order_item_stmt).scalars().first()
            print(f"🔍 Order item found: {order_item}, type: {type(order_item)}")
            if order_item:
                print(f"🔍 Order item details - id: {order_item.id}, order_id: {order_item.order_id}, order_quantity: {order_item.order_quantity}")
            if not order_item or order_item.order_id != request.order_id:
                return api_response(400, f"Invalid order item: {item.order_item_id}")

            order_qty = int(float(order_item.order_quantity)) if order_item.order_quantity else 0
            if item.quantity > order_qty:
                return api_response(400, f"Return quantity exceeds ordered quantity for item {item.order_item_id}")
            
            item_refund = (order_item.unit_price * item.quantity)
            return_item = ReturnItem(
                order_item_id=item.order_item_id,
                product_id=order_item.product_id,
                variation_option_id=order_item.variation_option_id,
                quantity=item.quantity,
                unit_price=order_item.unit_price,
                refund_amount=item_refund
            )
            return_items.append(return_item)
            refund_amount += item_refund

    # Create return request
    return_request = ReturnRequest(
        order_id=request.order_id,
        user_id=user.get("id"),
        return_type=request.return_type,
        reason=request.reason,
        refund_amount=refund_amount,
        return_items=return_items
    )

    session.add(return_request)
    session.flush()  # Get return_request.id before commit

    # ✅ UPDATE OrderProduct with return_request_id
    for return_item in return_items:
        order_product = session.execute(
            select(OrderProduct).where(OrderProduct.id == return_item.order_item_id)
        ).scalars().first()
        if order_product:
            order_product.return_request_id = return_request.id
            session.add(order_product)

    session.commit()
    session.refresh(return_request)

    # Send notifications
    from src.api.models.order_model.orderModel import OrderProduct as OP
    order_products = session.execute(select(OP).where(OP.order_id == order.id)).scalars().all()
    shop_ids = list(set([op.shop_id for op in order_products if op.shop_id]))

    NotificationHelper.notify_return_request_created(
        session=session,
        return_id=return_request.id,
        order_tracking_number=order.tracking_number,
        customer_id=order.customer_id,
        shop_ids=shop_ids
    )

    return api_response(201, "Return request created successfully", ReturnRequestRead.model_validate(return_request))


# ✅ APPROVE RETURN REQUEST
@router.put("/approve/{return_id}")
def approve_return_request(
    return_id: int,
    session: GetSession,
    background_tasks: BackgroundTasks = None,
    user=requirePermission("return:approve"),
):
    return_request = session.get(ReturnRequest, return_id)
    raiseExceptions((return_request, 404, "Return request not found"))

    if return_request.status != ReturnStatus.PENDING:
        return api_response(400, "Return request is not pending")

    # Update status
    return_request.status = ReturnStatus.APPROVED
    return_request.refund_status = RefundStatus.PENDING

    # Restock inventory and log transaction
    from src.api.models.product_model.productsModel import Product
    from src.api.models.product_model.variationOptionModel import VariationOption

    logger = TransactionLogger(session)

    from src.api.models.order_model.orderModel import OrderProduct

    for return_item in return_request.return_items:
        try:
            # ✅ UPDATE OrderProduct as returned
            order_product = session.execute(
                select(OrderProduct).where(OrderProduct.id == return_item.order_item_id)
            ).scalars().first()
            if order_product:
                order_product.is_returned = True
                order_product.returned_quantity = return_item.quantity
                session.add(order_product)
                print(f"✅ Marked order_product #{order_product.id} as returned (qty: {return_item.quantity})")

            if return_item.variation_option_id:
                # Handle variable product
                variation = session.get(VariationOption, return_item.variation_option_id)
                if variation:
                    previous_qty = variation.quantity
                    variation.quantity += return_item.quantity
                    session.add(variation)

                    # Update parent product quantity
                    product = session.get(Product, return_item.product_id)
                    if product:
                        product.quantity += return_item.quantity
                        session.add(product)

                        # Log order return transaction
                        logger.log_transaction(
                            TransactionLogCreate(
                                transaction_type=TransactionType.ORDER_RETURNED,
                                product_id=return_item.product_id,
                                variation_option_id=return_item.variation_option_id,
                                order_id=return_request.order_id,
                                shop_id=product.shop_id,
                                user_id=user.get("id") if user else None,
                                quantity_change=return_item.quantity,
                                unit_price=return_item.unit_price,
                                previous_quantity=previous_qty,
                                new_quantity=variation.quantity,
                                notes=f"Return request #{return_id} approved - stock restored"
                            )
                        )
            else:
                # Handle simple product
                product = session.get(Product, return_item.product_id)
                if product:
                    previous_qty = product.quantity
                    product.quantity += return_item.quantity
                    product.in_stock = True
                    session.add(product)

                    # Log order return transaction
                    logger.log_transaction(
                        TransactionLogCreate(
                            transaction_type=TransactionType.ORDER_RETURNED,
                            product_id=return_item.product_id,
                            order_id=return_request.order_id,
                            shop_id=product.shop_id,
                            user_id=user.get("id") if user else None,
                            quantity_change=return_item.quantity,
                            unit_price=return_item.unit_price,
                            previous_quantity=previous_qty,
                            new_quantity=product.quantity,
                            notes=f"Return request #{return_id} approved - stock restored"
                        )
                    )
        except Exception as e:
            print(f"Error restocking product {return_item.product_id}: {str(e)}")

    session.commit()

    # Send approval notifications
    from src.api.models.order_model.orderModel import Order, OrderProduct as OP
    order = session.get(Order, return_request.order_id)
    if order:
        order_products = session.execute(select(OP).where(OP.order_id == order.id)).scalars().all()
        shop_ids = list(set([op.shop_id for op in order_products if op.shop_id]))

        NotificationHelper.notify_return_request_approved(
            session=session,
            return_id=return_request.id,
            order_tracking_number=order.tracking_number,
            customer_id=return_request.user_id,
            shop_ids=shop_ids,
            refund_amount=float(return_request.refund_amount)
        )

    # Process refund in background
    if background_tasks:
        background_tasks.add_task(process_refund, return_request.id)

    return api_response(200, "Return request approved", ReturnRequestRead.model_validate(return_request))


# ✅ REJECT RETURN REQUEST
@router.put("/reject/{return_id}")
def reject_return_request(
    return_id: int,
    rejected_reason: str,
    session: GetSession,
    user=requirePermission("return:reject"),
):
    return_request = session.get(ReturnRequest, return_id)
    raiseExceptions((return_request, 404, "Return request not found"))

    if return_request.status != ReturnStatus.PENDING:
        return api_response(400, "Return request is not pending")

    return_request.status = ReturnStatus.REJECTED
    return_request.rejected_reason = rejected_reason

    # ✅ Clear return_request_id from OrderProduct so user can create new return request
    from src.api.models.order_model.orderModel import Order, OrderProduct
    for return_item in return_request.return_items:
        order_product = session.execute(
            select(OrderProduct).where(OrderProduct.id == return_item.order_item_id)
        ).scalars().first()
        if order_product:
            order_product.return_request_id = None
            session.add(order_product)
            print(f"✅ Cleared return_request_id from order_product #{order_product.id}")

    session.commit()

    # Send rejection notification
    order = session.get(Order, return_request.order_id)
    if order:
        NotificationHelper.notify_return_request_rejected(
            session=session,
            return_id=return_request.id,
            order_tracking_number=order.tracking_number,
            customer_id=return_request.user_id,
            reason=rejected_reason
        )

    return api_response(200, "Return request rejected", ReturnRequestRead.model_validate(return_request))


# ✅ PROCESS REFUND (Internal/Admin)
def process_refund(return_id: int):
    """Background task to process refund to wallet"""
    from src.lib.db_con import engine
    from sqlmodel import Session

    with Session(engine) as session:
        return_request = session.get(ReturnRequest, return_id)

        # Check if return request exists and is approved
        if not return_request or return_request.status != ReturnStatus.APPROVED:
            print(f"⚠️ Return #{return_id} not found or not approved")
            return {"success": False, "message": "Return request not found or not approved"}

        # ✅ DUPLICATE CHECK: Skip if already processed
        if return_request.refund_status == RefundStatus.PROCESSED:
            print(f"⚠️ Return #{return_id} already processed - skipping to prevent duplicate")
            return {"success": False, "message": "Refund already processed", "already_processed": True}

        # ✅ DUPLICATE CHECK: Check if wallet transaction already exists for this return
        existing_transaction = session.execute(
            select(WalletTransaction).where(
                WalletTransaction.return_request_id == return_id,
                WalletTransaction.transaction_type == "credit"
            )
        ).scalars().first()

        if existing_transaction:
            print(f"⚠️ Wallet transaction already exists for return #{return_id} - skipping")
            # Update refund_status if not set
            if return_request.refund_status != RefundStatus.PROCESSED:
                return_request.refund_status = RefundStatus.PROCESSED
                return_request.wallet_credit_id = existing_transaction.id
                session.commit()
            return {"success": False, "message": "Wallet transaction already exists", "transaction_id": existing_transaction.id}

        try:
            # Get or create user wallet
            user_wallet = session.execute(
                select(UserWallet).where(UserWallet.user_id == return_request.user_id)
            ).scalars().first()

            if not user_wallet:
                user_wallet = UserWallet(user_id=return_request.user_id, balance=0.0, total_credited=0.0, total_debited=0.0)
                session.add(user_wallet)
                session.commit()
                session.refresh(user_wallet)

            # Credit amount to wallet
            new_balance = float(user_wallet.balance) + float(return_request.refund_amount)

            # Create wallet transaction
            wallet_transaction = WalletTransaction(
                user_id=return_request.user_id,
                amount=return_request.refund_amount,
                transaction_type="credit",
                balance_after=new_balance,
                description=f"Refund for return #{return_request.id}",
                is_refund=True,
                transfer_eligible_at=datetime.utcnow() + timedelta(days=15),
                return_request_id=return_request.id
            )
            session.add(wallet_transaction)
            session.flush()  # Get the ID

            # Update wallet balance
            user_wallet.balance = new_balance
            user_wallet.total_credited = float(user_wallet.total_credited or 0) + float(return_request.refund_amount)

            # Update return request
            return_request.refund_status = RefundStatus.PROCESSED
            return_request.wallet_credit_id = wallet_transaction.id
            return_request.transfer_eligible_at = wallet_transaction.transfer_eligible_at

            session.commit()

            print(f"✅ Refund processed for return #{return_id}: ${return_request.refund_amount}")
            return {
                "success": True,
                "message": "Refund processed successfully",
                "refund_amount": float(return_request.refund_amount),
                "new_balance": new_balance,
                "transaction_id": wallet_transaction.id
            }

        except Exception as e:
            session.rollback()
            return_request.refund_status = RefundStatus.FAILED
            session.commit()
            print(f"❌ Refund failed for return #{return_id}: {str(e)}")
            return {"success": False, "message": f"Refund failed: {str(e)}"}


# ✅ TEST ROUTE: Process Refund (for debugging)
@router.post("/test-process-refund/{return_id}")
def test_process_refund(
    return_id: int,
    session: GetSession,
    user=requirePermission("return:approve"),
):
    """
    Test route to manually trigger process_refund for debugging.
    Protected by admin permission.
    """
    # Get return request info before processing
    return_request = session.get(ReturnRequest, return_id)
    if not return_request:
        return api_response(404, "Return request not found")

    # Get current wallet balance
    user_wallet = session.execute(
        select(UserWallet).where(UserWallet.user_id == return_request.user_id)
    ).scalars().first()

    before_info = {
        "return_id": return_id,
        "return_status": return_request.status.value if return_request.status else None,
        "refund_status": return_request.refund_status.value if return_request.refund_status else None,
        "refund_amount": float(return_request.refund_amount) if return_request.refund_amount else 0,
        "wallet_balance_before": float(user_wallet.balance) if user_wallet else 0,
        "existing_wallet_credit_id": return_request.wallet_credit_id
    }

    # Process the refund
    result = process_refund(return_id)

    # Get updated info
    session.refresh(return_request)
    user_wallet_after = session.execute(
        select(UserWallet).where(UserWallet.user_id == return_request.user_id)
    ).scalars().first()

    after_info = {
        "refund_status_after": return_request.refund_status.value if return_request.refund_status else None,
        "wallet_balance_after": float(user_wallet_after.balance) if user_wallet_after else 0,
        "wallet_credit_id": return_request.wallet_credit_id
    }

    return api_response(
        200 if result.get("success") else 400,
        result.get("message", "Process completed"),
        {
            "before": before_info,
            "after": after_info,
            "process_result": result
        }
    )


# ✅ GET MY RETURN REQUESTS
@router.get("/my-returns", response_model=list[ReturnRequestRead])
def get_my_returns(
    query_params: ListQueryParams,
    session: GetSession,
    user:requireSignin
):
    query_params = vars(query_params)
    
    if "filters" not in query_params:
        query_params["filters"] = {}
    query_params["filters"]["user_id"] = user.get("id")
    
    return listRecords(
        query_params=query_params,
        searchFields=["reason"],
        Model=ReturnRequest,
        Schema=ReturnRequestRead,
    )


# ✅ GET ALL RETURN REQUESTS (Admin)
@router.get("/list", response_model=list[ReturnRequestRead])
def list_all_returns(
    query_params: ListQueryParams,
    user=requirePermission("return:view_all")
):
    query_params = vars(query_params)
    
    return listRecords(
        query_params=query_params,
        searchFields=["reason"],
        Model=ReturnRequest,
        Schema=ReturnRequestRead,
    )


# ✅ GET RETURN BY ID
@router.get("/{return_id}")
def get_return_request(
    return_id: int,
    session: GetSession,
    user:requireSignin
):
    return_request = session.get(ReturnRequest, return_id)
    raiseExceptions((return_request, 404, "Return request not found"))

    # Users can only see their own returns, admin can see all
    if return_request.user_id != user.get("id") and not user.has_permission("return:view_all"):
        return api_response(403, "Not authorized to view this return")

    return api_response(200, "Return request found", ReturnRequestRead.model_validate(return_request))