# src/api/routes/returnRoute.py
from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import select, func
from datetime import datetime, timedelta
from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listRecords, updateOp
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

router = APIRouter(prefix="/returns", tags=["Returns & Refunds"])


# ✅ CREATE RETURN REQUEST
@router.post("/request")
def create_return_request(
    request: ReturnRequestCreate,
    session: GetSession,
    user=requireSignin,
    background_tasks: BackgroundTasks = None,
):
    print("🔄 Creating return request:", request.model_dump())
    print ("User signin:",user)
    # Verify order exists and belongs to user
    from src.api.models.order_model.orderModel import Order, OrderProduct
    order = session.get(Order, request.order_id)
    raiseExceptions((order, 404, "Order not found"))
    print ("order detail:",order)
    if order.customer_id != user:
        return api_response(403, "Not authorized to return this order")

    # Check if order is eligible for return
    if order.status not in ["delivered", "completed"]:
        return api_response(400, "Order is not eligible for return")

    # Check if return period has expired (e.g., 30 days)
    return_period_days = 30
    if (datetime.utcnow() - order.delivered_at).days > return_period_days:
        return api_response(400, "Return period has expired")

    # Calculate refund amount based on return type
    refund_amount = 0.0
    
    if request.return_type == ReturnType.FULL_ORDER:
        refund_amount = order.total_amount
        return_items = []
        
        # Create return items for all order items
        for order_item in order.order_items:
            return_item = ReturnItem(
                order_item_id=order_item.id,
                product_id=order_item.product_id,
                variation_option_id=order_item.variation_option_id,
                quantity=order_item.quantity,
                unit_price=order_item.unit_price,
                refund_amount=order_item.total_price
            )
            return_items.append(return_item)
            refund_amount += order_item.total_price
            
    else:  # SINGLE_PRODUCT
        return_items = []
        for item in request.items:
            order_item = session.get(OrderProduct, item.order_item_id)
            if not order_item or order_item.order_id != request.order_id:
                return api_response(400, f"Invalid order item: {item.order_item_id}")
            
            if item.quantity > order_item.quantity:
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
        user_id=user.id,
        return_type=request.return_type,
        reason=request.reason,
        refund_amount=refund_amount,
        return_items=return_items
    )

    session.add(return_request)
    session.commit()
    session.refresh(return_request)

    # Notify admin (background task)
    if background_tasks:
        background_tasks.add_task(notify_admin_about_return, return_request.id)

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

    session.commit()

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

    session.commit()

    return api_response(200, "Return request rejected", ReturnRequestRead.model_validate(return_request))


# ✅ PROCESS REFUND (Internal/Admin)
def process_refund(return_id: int):
    """Background task to process refund to wallet"""
    from src.api.core.database import get_db_session
    
    with get_db_session() as session:
        return_request = session.get(ReturnRequest, return_id)
        if not return_request or return_request.status != ReturnStatus.APPROVED:
            return
        
        try:
            # Get or create user wallet
            user_wallet = session.exec(
                select(UserWallet).where(UserWallet.user_id == return_request.user_id)
            ).first()
            
            if not user_wallet:
                user_wallet = UserWallet(user_id=return_request.user_id, balance=0.0)
                session.add(user_wallet)
                session.commit()
                session.refresh(user_wallet)
            
            # Credit amount to wallet
            new_balance = user_wallet.balance + return_request.refund_amount
            
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
            
            # Update wallet balance
            user_wallet.balance = new_balance
            user_wallet.total_credited += return_request.refund_amount
            
            # Update return request
            return_request.refund_status = RefundStatus.PROCESSED
            return_request.wallet_credit_id = wallet_transaction.id
            return_request.transfer_eligible_at = wallet_transaction.transfer_eligible_at
            
            session.add(wallet_transaction)
            session.commit()
            
            print(f"✅ Refund processed for return #{return_id}: ${return_request.refund_amount}")
            
        except Exception as e:
            session.rollback()
            return_request.refund_status = RefundStatus.FAILED
            session.commit()
            print(f"❌ Refund failed for return #{return_id}: {str(e)}")


# ✅ GET MY RETURN REQUESTS
@router.get("/my-returns", response_model=list[ReturnRequestRead])
def get_my_returns(
    query_params: ListQueryParams,
    session: GetSession,
    user=requireSignin
):
    query_params = vars(query_params)
    
    if "filters" not in query_params:
        query_params["filters"] = {}
    query_params["filters"]["user_id"] = user.id
    
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
    user=requireSignin
):
    return_request = session.get(ReturnRequest, return_id)
    raiseExceptions((return_request, 404, "Return request not found"))

    # Users can only see their own returns, admin can see all
    if return_request.user_id != user.id and not user.has_permission("return:view_all"):
        return api_response(403, "Not authorized to view this return")

    return api_response(200, "Return request found", ReturnRequestRead.model_validate(return_request))