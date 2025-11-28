# src/api/routes/withdrawRoute.py
from fastapi import APIRouter, Query
from sqlalchemy import select, func
from typing import Optional
from decimal import Decimal
from datetime import datetime
from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listop
from src.api.core.dependencies import GetSession, requirePermission, requireSignin
from src.api.models.withdrawModel import (
    ShopWithdrawRequest, WithdrawRequestCreate, WithdrawRequestUpdate, 
    WithdrawRequestRead, WithdrawStatus, PaymentMethod, ShopEarning,
    ShopBalanceSummary, ShopEarningRead
)
from src.api.models.shop_model.shopsModel import Shop
from src.api.models.order_model.orderModel import Order, OrderStatusEnum, OrderProduct

router = APIRouter(prefix="/withdraw", tags=["Withdraw Requests"])
def get_shop_id_from_result(shop_result):
    """Extract shop ID from SQLAlchemy result"""
    if hasattr(shop_result, '__getitem__') and len(shop_result) > 0:
        return shop_result[0].id
    elif hasattr(shop_result, 'id'):
        return shop_result.id
    else:
        raise ValueError("Unable to extract shop ID from result")
def calculate_shop_balance(session, shop_id: int, include_shop_info: bool = False) -> ShopBalanceSummary:
    """Calculate shop's current balance and earnings"""
    # Get total earnings from completed orders for this specific shop
    total_earnings_stmt = select(
        func.coalesce(func.sum(ShopEarning.shop_earning), 0),
        func.coalesce(func.sum(ShopEarning.admin_commission), 0)
    ).where(
        ShopEarning.shop_id == shop_id,
        ShopEarning.is_settled == False
    )
    total_result = session.exec(total_earnings_stmt).first()
    total_earnings = total_result[0] or Decimal("0.00")
    total_commission = total_result[1] or Decimal("0.00")

    # Get pending withdrawals
    pending_withdrawals_stmt = select(
        func.coalesce(func.sum(ShopWithdrawRequest.amount), 0)
    ).where(
        ShopWithdrawRequest.shop_id == shop_id,
        ShopWithdrawRequest.status.in_([WithdrawStatus.PENDING, WithdrawStatus.APPROVED])
    )
    pending_withdrawals = session.exec(pending_withdrawals_stmt).scalar() or Decimal("0.00")

    net_balance = total_earnings
    available_balance = net_balance - pending_withdrawals

    # Get shop info if requested
    shop_name = None
    if include_shop_info:
        shop = session.get(Shop, shop_id)
        shop_name = shop.name if shop else "Unknown"

    return ShopBalanceSummary(
        shop_id=shop_id if include_shop_info else None,
        shop_name=shop_name,
        total_earnings=total_earnings,
        total_admin_commission=total_commission,
        net_balance=net_balance,
        pending_withdrawals=pending_withdrawals,
        available_balance=available_balance
    )

@router.post("/request")
def create_withdraw_request(
    request: WithdrawRequestCreate,
    session: GetSession,
    user: requireSignin
):
    """Shop owner creates a withdrawal request for a specific shop"""
    # Get shop by ID and verify ownership
    shop = session.get(Shop, request.shop_id)
    raiseExceptions((shop, 404, f"Shop with ID {request.shop_id} not found"))

    # Verify user owns this shop
    if shop.owner_id != user.get("id"):
        return api_response(403, "You don't have permission to create withdrawal request for this shop")

    # Calculate available balance for this shop
    balance = calculate_shop_balance(session, request.shop_id,True)
    print(f"balance:{balance}")
    
    if request.amount > balance.available_balance:
        return api_response(400, f"Insufficient balance. Available: ${balance.available_balance}")

    if request.amount <= 0:
        return api_response(400, "Withdrawal amount must be greater than 0")

    # Calculate admin commission (5% of withdrawal amount)
    #admin_commission = request.amount * Decimal("0.05")
    net_amount = request.amount #- admin_commission
    admin_commission=balance.total_admin_commission
    # Create withdrawal request
    withdraw_request = ShopWithdrawRequest(
        shop_id=request.shop_id,
        amount=request.amount,
        admin_commission=admin_commission,
        net_amount=net_amount,
        payment_method=request.payment_method,
        bank_name=request.bank_name,
        account_number=request.account_number,
        account_holder_name=request.account_holder_name,
        ifsc_code=request.ifsc_code
    )

    session.add(withdraw_request)
    session.commit()
    session.refresh(withdraw_request)

    return api_response(201, "Withdrawal request created successfully",
                       WithdrawRequestRead.model_validate(withdraw_request))

@router.get("/shop-balance")
def get_all_shop_balances(session: GetSession, user: requireSignin):
    """Get balance summary for all shops owned by logged-in user"""
    # Get all shops owned by user
    shops = session.exec(
        select(Shop).where(Shop.owner_id == user.get("id"))
    ).scalars().all()

    if not shops:
        return api_response(404, "No shops found for this user")

    # Calculate balance for each shop
    balances = []
    for shop in shops:
        balance = calculate_shop_balance(session, shop.id, include_shop_info=True)
        balances.append(balance)

    return api_response(
        200,
        f"Balance retrieved for {len(balances)} shop(s)",
        balances,
        len(balances)
    )


@router.get("/shop-balance/{shop_id}")
def get_single_shop_balance(shop_id: int, session: GetSession, user: requireSignin):
    """Get balance summary for a specific shop"""
    # Get shop and verify ownership
    shop = session.get(Shop, shop_id)
    raiseExceptions((shop, 404, "Shop not found"))

    # Verify user owns this shop
    if shop.owner_id != user.get("id"):
        return api_response(403, "You don't have access to this shop")

    balance = calculate_shop_balance(session, shop_id, include_shop_info=True)

    return api_response(200, "Balance retrieved successfully", balance)

@router.get("/my-requests")
def get_my_withdraw_requests(
    session: GetSession,
    user: requireSignin,
    shop_id: Optional[int] = Query(None, description="Filter by specific shop ID"),
    skip: int = 0,
    limit: int = Query(50, ge=1, le=200)
):
    """Get withdrawal requests for all shops owned by logged-in user (or filter by shop_id)"""
    # Get all shops owned by user
    user_shops = session.exec(
        select(Shop).where(Shop.owner_id == user.get("id"))
    ).scalars().all()

    if not user_shops:
        return api_response(404, "No shops found for this user")

    # Get list of user's shop IDs
    user_shop_ids = [shop.id for shop in user_shops]

    # If shop_id filter is provided, verify user owns it
    if shop_id:
        if shop_id not in user_shop_ids:
            return api_response(403, "You don't have access to this shop")
        # Filter by specific shop
        query = select(ShopWithdrawRequest).where(
            ShopWithdrawRequest.shop_id == shop_id
        )
        count_query = select(func.count(ShopWithdrawRequest.id)).where(
            ShopWithdrawRequest.shop_id == shop_id
        )
    else:
        # Get requests for all user's shops
        query = select(ShopWithdrawRequest).where(
            ShopWithdrawRequest.shop_id.in_(user_shop_ids)
        )
        count_query = select(func.count(ShopWithdrawRequest.id)).where(
            ShopWithdrawRequest.shop_id.in_(user_shop_ids)
        )

    query = query.order_by(ShopWithdrawRequest.created_at.desc())

    requests = session.exec(query.offset(skip).limit(limit)).scalars().all()
    total = session.exec(count_query).scalar()

    # Include shop name in response
    requests_data = []
    for req in requests:
        req_data = WithdrawRequestRead.model_validate(req)
        req_data.shop_name = req.shop.name if req.shop else "Unknown"
        requests_data.append(req_data)

    return api_response(200, "Requests retrieved", requests_data, total)

@router.get("/list")
def list_withdraw_requests(
    session: GetSession,
    status: Optional[WithdrawStatus] = None,
    shop_id: Optional[int] = None,
    skip: int = 0,
    limit: int = Query(50, ge=1, le=100),
    user=requirePermission("withdraw:view_all")
):
    """Admin: List all withdrawal requests with filters"""
    query = select(ShopWithdrawRequest)
    
    if status:
        query = query.where(ShopWithdrawRequest.status == status)
    if shop_id:
        query = query.where(ShopWithdrawRequest.shop_id == shop_id)
    
    query = query.order_by(ShopWithdrawRequest.created_at.desc())

    requests = session.exec(query.offset(skip).limit(limit)).scalars().all()
    total = session.exec(select(func.count(ShopWithdrawRequest.id))).scalar()

    # Include shop name in response
    requests_data = []
    for req in requests:
        req_data = WithdrawRequestRead.model_validate(req)
        req_data.shop_name = req.shop.name if req.shop else "Unknown"
        requests_data.append(req_data)

    return api_response(200, "Requests retrieved", requests_data, total)

@router.put("/approve/{request_id}")
def approve_withdraw_request(
    request_id: int,
    session: GetSession,
    user=requirePermission("withdraw:approve")
):
    """Admin: Approve a withdrawal request"""
    withdraw_request = session.get(ShopWithdrawRequest, request_id)
    print(f"withdraw_request:{withdraw_request}")
    raiseExceptions((withdraw_request, 404, "Withdrawal request not found"))
    
    if withdraw_request.status != WithdrawStatus.PENDING:
        return api_response(400, "Request is not in pending status")
    
    # Verify shop has sufficient balance
    balance = calculate_shop_balance(session, withdraw_request.shop_id, True)
    print(f"balance:{balance}")
    print(f"user:{user.get('id')}")

    if withdraw_request.amount > balance.net_balance:
        return api_response(400, "Shop has insufficient balance")

    withdraw_request.status = WithdrawStatus.APPROVED
    withdraw_request.processed_by = user.get("id")
    withdraw_request.processed_at = datetime.now()

    session.commit()

    return api_response(200, "Withdrawal request approved",
                       WithdrawRequestRead.model_validate(withdraw_request))

@router.put("/reject/{request_id}")
def reject_withdraw_request(
    request_id: int,
    rejection_reason: str,
    session: GetSession,
    user=requirePermission("withdraw:approve")
):
    """Admin: Reject a withdrawal request"""
    withdraw_request = session.get(ShopWithdrawRequest, request_id)
    raiseExceptions((withdraw_request, 404, "Withdrawal request not found"))
    
    if withdraw_request.status != WithdrawStatus.PENDING:
        return api_response(400, "Request is not in pending status")
    
    withdraw_request.status = WithdrawStatus.REJECTED
    withdraw_request.rejection_reason = rejection_reason
    withdraw_request.processed_by = user.get("id")
    withdraw_request.processed_at = datetime.now()
    
    session.commit()
    
    return api_response(200, "Withdrawal request rejected", 
                       WithdrawRequestRead.model_validate(withdraw_request))

@router.put("/process/{request_id}")
def process_withdraw_request(
    request_id: int,
    session: GetSession,
    user=requirePermission("withdraw:process")
):
    """Admin: Mark withdrawal as processed (money transferred)"""
    withdraw_request = session.get(ShopWithdrawRequest, request_id)
    raiseExceptions((withdraw_request, 404, "Withdrawal request not found"))
    
    if withdraw_request.status != WithdrawStatus.APPROVED:
        return api_response(400, "Request must be approved before processing")
    
    # Mark associated earnings as settled (only for this specific shop)
    earnings_to_settle = session.exec(
        select(ShopEarning).where(
            ShopEarning.shop_id == withdraw_request.shop_id,
            ShopEarning.is_settled == False
        ).order_by(ShopEarning.created_at.asc())  # Settle oldest earnings first
    ).scalars().all()

    # Simple settlement: mark oldest earnings first until amount is covered
    amount_settled = Decimal("0.00")
    for earning in earnings_to_settle:
        if amount_settled < withdraw_request.amount:
            earning.is_settled = True
            earning.settled_at = datetime.now()
            amount_settled += earning.shop_earning
            session.add(earning)

    withdraw_request.status = WithdrawStatus.PROCESSED

    session.commit()

    return api_response(200, "Withdrawal processed successfully",
                       WithdrawRequestRead.model_validate(withdraw_request))

@router.get("/shop-earnings")
def get_shop_earnings(
    user:requireSignin,
    session: GetSession,
    settled: Optional[bool] = None,
    skip: int = 0,
    limit: int = Query(50, ge=1, le=100)
):
    """Get shop earnings history"""
    shop = session.exec(
        select(Shop).where(Shop.owner_id == user["id"])
    ).first()
    raiseExceptions((shop, 404, "Shop not found"))
    
    # FIX: Access shop ID correctly
    shop_id = get_shop_id_from_result(shop)
    query = select(ShopEarning).where(ShopEarning.shop_id == shop_id)
    
    if settled is not None:
        query = query.where(ShopEarning.is_settled == settled)
    
    query = query.order_by(ShopEarning.created_at.desc())

    earnings = session.exec(query.offset(skip).limit(limit)).scalars().all()
    total = session.exec(select(func.count(ShopEarning.id)).where(
        ShopEarning.shop_id == shop_id
    )).scalar()

    earnings_data = []
    for earning in earnings:
        earning_data = ShopEarningRead.model_validate(earning)
        earning_data.order_tracking_number = earning.order.tracking_number if earning.order else "Unknown"
        earnings_data.append(earning_data)
    
    return api_response(200, "Earnings retrieved", earnings_data, total)