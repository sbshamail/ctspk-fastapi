from fastapi import APIRouter, Request, Query
from fastapi.responses import RedirectResponse
from typing import Optional
from decimal import Decimal

from src.api.core.response import api_response
from src.api.core.dependencies import GetSession, requireSignin, isAuthenticated
from src.api.core.payment.payment_helper import PaymentHelper
from src.api.core.payment.gateway_factory import PaymentGatewayFactory
from src.api.models.order_model.orderModel import Order
from src.api.models.payment_model.paymentTransactionModel import RefundRequest
from src.config import DOMAIN

router = APIRouter(prefix="/payment", tags=["Payment"])


# ============================================
# GATEWAY INFORMATION
# ============================================


@router.get("/gateways")
def get_available_gateways(session: GetSession):
    """Get list of available payment gateways"""
    gateways = PaymentGatewayFactory.get_available_gateways()
    return api_response(200, "Payment gateways retrieved", gateways)


@router.get("/gateway/{gateway_name}/available")
def check_gateway_availability(gateway_name: str):
    """Check if a specific gateway is available"""
    available = PaymentGatewayFactory.is_gateway_available(gateway_name)
    return api_response(
        200, "Gateway availability checked", {"name": gateway_name, "available": available}
    )


# ============================================
# PAYMENT INITIATION
# ============================================


@router.post("/initiate/{order_id}")
def initiate_payment(
    order_id: int,
    gateway_name: str = Query(..., description="Payment gateway name"),
    session: GetSession = None,
    request: Request = None,
    user: isAuthenticated = None,
):
    """
    Initiate payment for an order.

    For redirect-based gateways: Returns redirect URL
    For API-based gateways: Returns payment data
    """
    # Get order
    order = session.get(Order, order_id)
    if not order:
        return api_response(404, "Order not found")

    # Verify ownership (if user is logged in)
    if user and order.customer_id and order.customer_id != user.get("id"):
        return api_response(403, "You don't have access to this order")

    # Get client info
    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None

    success, result = PaymentHelper.initiate_payment(
        session=session,
        order_id=order_id,
        gateway_name=gateway_name,
        amount=Decimal(str(order.total)),
        customer_id=user.get("id") if user else None,
        customer_name=order.customer_name,
        customer_email=user.get("email") if user else None,
        customer_phone=order.customer_contact,
        description=f"Order #{order.tracking_number}",
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if success:
        return api_response(200, "Payment initiated", result)
    else:
        return api_response(400, result.get("error", "Payment initiation failed"), result)


# ============================================
# PAYMENT CALLBACKS (Gateway Redirects)
# ============================================


@router.get("/callback/{gateway_name}")
async def payment_callback_get(
    gateway_name: str,
    session: GetSession,
    request: Request,
):
    """Handle GET callback from payment gateway"""
    callback_data = dict(request.query_params)

    success, transaction_id, result = PaymentHelper.process_callback(
        session, gateway_name, callback_data
    )

    # Redirect to frontend with result
    frontend_url = f"{DOMAIN}/payment/result"
    status = "success" if success else "failed"

    return RedirectResponse(
        url=f"{frontend_url}?status={status}&transaction_id={transaction_id}"
    )


@router.post("/callback/{gateway_name}")
async def payment_callback_post(
    gateway_name: str,
    session: GetSession,
    request: Request,
):
    """Handle POST callback from payment gateway"""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        callback_data = await request.json()
    else:
        form = await request.form()
        callback_data = dict(form)

    success, transaction_id, result = PaymentHelper.process_callback(
        session, gateway_name, callback_data
    )

    if success:
        return api_response(200, "Payment successful", result)
    else:
        return api_response(400, "Payment failed", result)


@router.get("/cancel/{gateway_name}")
async def payment_cancel(
    gateway_name: str,
    request: Request,
):
    """Handle payment cancellation redirect"""
    token = request.query_params.get("token", "")

    # Redirect to frontend with cancellation status
    frontend_url = f"{DOMAIN}/payment/result"

    return RedirectResponse(
        url=f"{frontend_url}?status=cancelled&transaction_id={token}"
    )


# ============================================
# WEBHOOKS (Server-to-Server)
# ============================================


@router.post("/webhook/{gateway_name}")
async def payment_webhook(
    gateway_name: str,
    session: GetSession,
    request: Request,
):
    """Handle webhook/IPN from payment gateway"""
    payload = await request.body()
    headers = dict(request.headers)

    success, result = PaymentHelper.process_webhook(
        session, gateway_name, payload, headers
    )

    # Always return 200 to acknowledge receipt (prevent retries)
    if success:
        return {"status": "ok"}
    else:
        print(f"Webhook processing error for {gateway_name}: {result}")
        return {"status": "ok"}


# ============================================
# PAYMENT VERIFICATION
# ============================================


@router.get("/verify/{transaction_id}")
def verify_payment(
    transaction_id: str,
    session: GetSession,
    session_id: Optional[str] = Query(None, description="Stripe session ID"),
):
    """Verify payment status"""
    verification_data = {}
    if session_id:
        verification_data["session_id"] = session_id

    success, result = PaymentHelper.verify_payment(
        session, transaction_id, verification_data=verification_data
    )

    if success:
        return api_response(200, "Payment verified", result)
    else:
        return api_response(400, result.get("error", "Verification failed"), result)


@router.get("/status/{transaction_id}")
def get_payment_status(
    transaction_id: str,
    session: GetSession,
):
    """Get transaction status"""
    result = PaymentHelper.get_transaction_status(session, transaction_id)

    if "error" in result:
        return api_response(404, result["error"])

    return api_response(200, "Transaction status retrieved", result)


# ============================================
# REFUNDS
# ============================================


@router.post("/refund")
def refund_payment(
    request: RefundRequest,
    session: GetSession,
    user: requireSignin = None,
):
    """Process a refund (requires authentication)"""
    success, result = PaymentHelper.refund_payment(
        session=session,
        transaction_id=request.transaction_id,
        amount=request.amount,
        reason=request.reason,
    )

    if success:
        return api_response(200, "Refund processed", result)
    else:
        return api_response(400, result.get("error", "Refund failed"), result)


# ============================================
# ORDER TRANSACTIONS
# ============================================


@router.get("/order/{order_id}/transactions")
def get_order_transactions(
    order_id: int,
    session: GetSession,
    user: isAuthenticated = None,
):
    """Get all transactions for an order"""
    # Verify order exists
    order = session.get(Order, order_id)
    if not order:
        return api_response(404, "Order not found")

    # Verify ownership (if user is logged in)
    if user and order.customer_id and order.customer_id != user.get("id"):
        return api_response(403, "You don't have access to this order")

    transactions = PaymentHelper.get_order_transactions(session, order_id)
    return api_response(200, "Transactions retrieved", transactions)
