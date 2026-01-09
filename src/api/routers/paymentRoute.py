from fastapi import APIRouter, Request, Query
from fastapi.responses import RedirectResponse
from typing import Optional
from decimal import Decimal

from src.api.core.response import api_response
from src.api.core.dependencies import GetSession, requireSignin, isAuthenticated
from src.api.core.payment.payment_helper import PaymentHelper
from src.api.core.payment.gateway_factory import PaymentGatewayFactory
from src.api.models.order_model.orderModel import Order
from src.api.models.payment_model.paymentTransactionModel import RefundRequest, PayFastCreatePaymentRequest
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
# PAYFAST DIRECT PAYMENT
# ============================================


@router.post("/payfast/create-payment")
def payfast_create_payment(
    request: PayFastCreatePaymentRequest,
):
    """
    Generate PayFast payment UUID for onsite payment modal.
    Calls PayFast API to get ACCESS_TOKEN for embedded checkout.
    """
    import httpx
    import hashlib
    from datetime import datetime
    from src.config import (
        PAYFAST_MERCHANT_ID,
        PAYFAST_SECURED_KEY,
        PAYFAST_BASE_URL,
        PAYFAST_RETURN_URL,
        PAYFAST_CANCEL_URL,
    )

    if not all([PAYFAST_MERCHANT_ID, PAYFAST_SECURED_KEY, PAYFAST_BASE_URL]):
        return api_response(500, "PayFast gateway not configured")

    # Build request data for PayFast
    customer_name = f"{request.customerFirstName} {request.customerLastName}"
    amount_in_paisa = str(int(request.amount * 100))

    request_data = {
        "MERCHANT_ID": PAYFAST_MERCHANT_ID,
        "MERCHANT_NAME": "CTSPK Store",
        "TOKEN": request.orderId,
        "PROCCODE": "00",
        "TXNAMT": amount_in_paisa,
        "CUSTOMER_MOBILE_NO": request.customerPhone or "",
        "CUSTOMER_EMAIL_ADDRESS": request.customerEmail or "",
        "VERSION": "MERCHANT-CART-0.1",
        "TXNDESC": request.itemDescription or request.itemName,
        "SUCCESS_URL": PAYFAST_RETURN_URL,
        "FAILURE_URL": PAYFAST_CANCEL_URL,
        "BASKET_ID": request.orderId,
        "ORDER_DATE": datetime.now().strftime("%Y%m%d%H%M%S"),
        "CHECKOUT_URL": f"{PAYFAST_RETURN_URL}?token={request.orderId}",
        "SECURED_KEY": PAYFAST_SECURED_KEY,
    }

    # Call PayFast API to get ACCESS_TOKEN for onsite checkout
    try:
        # Use GetToken endpoint for onsite modal
        api_url = f"{PAYFAST_BASE_URL}/Ecommerce/api/Transaction/GetAccessToken"

        with httpx.Client(timeout=30.0, verify=False) as client:
            # Try JSON first
            response = client.post(
                api_url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            # If JSON fails with 204/404, try form-encoded
            if response.status_code in [204, 404, 405]:
                api_url = f"{PAYFAST_BASE_URL}/Ecommerce/api/Transaction/PostTransaction"
                response = client.post(
                    api_url,
                    data=request_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

            # Debug: log raw response
            print(f"PayFast Response Status: {response.status_code}")
            print(f"PayFast Response Text: {response.text}")

            # Try to parse JSON response
            try:
                response_data = response.json()
            except Exception:
                # If not JSON, return raw response for debugging
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=200, content={
                    "success": 0,
                    "detail": "PayFast returned non-JSON response",
                    "data": {
                        "status_code": response.status_code,
                        "raw_response": response.text[:500] if response.text else "empty",
                        "request_url": api_url,
                        "request_data": {k: v for k, v in request_data.items() if k != "SECURED_KEY"},
                    }
                })

        # Check if we got ACCESS_TOKEN (try different key names)
        access_token = (
            response_data.get("ACCESS_TOKEN") or
            response_data.get("access_token") or
            response_data.get("Token") or
            response_data.get("token") or
            response_data.get("CHECKOUT_TOKEN")
        )

        if access_token:
            return api_response(200, "Payment token generated", {
                "accessToken": access_token,
                "transactionId": request.orderId,
                "merchantId": PAYFAST_MERCHANT_ID,
                "amount": float(request.amount),
                "response": response_data,
            })
        else:
            # Return full response for debugging
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=200, content={
                "success": 0,
                "detail": response_data.get("MESSAGE") or response_data.get("message") or response_data.get("errorDescription") or "Failed to generate payment token",
                "data": {
                    "response": response_data,
                    "request_url": api_url,
                    "request_data": {k: v for k, v in request_data.items() if k != "SECURED_KEY"},
                }
            })

    except httpx.RequestError as e:
        return api_response(500, f"PayFast API request failed: {str(e)}")
    except Exception as e:
        return api_response(500, f"Payment creation failed: {str(e)}")


@router.post("/confirm")
async def confirm_payment(
    request: Request,
    session: GetSession,
):
    """
    Confirm/update payment status for an order.
    Called by frontend after PayFast payment completion.

    Expected payload:
    {
        "tracking_number": "ORDER-123",
        "payment_status": "payment-success" | "payment-failed" | "payment-pending"
    }
    """
    from sqlmodel import select
    from src.api.models.order_model.orderModel import PaymentStatusEnum

    # Parse request body
    try:
        data = await request.json()
    except Exception:
        return api_response(400, "Invalid JSON payload")

    tracking_number = data.get("tracking_number")
    payment_status = data.get("payment_status")

    if not tracking_number:
        return api_response(400, "tracking_number is required")

    if not payment_status:
        return api_response(400, "payment_status is required")

    # Map frontend status strings to enum values
    status_mapping = {
        "payment-success": PaymentStatusEnum.SUCCESS.value,
        "payment-failed": PaymentStatusEnum.FAILED.value,
        "payment-pending": PaymentStatusEnum.PENDING.value,
        "payment-processing": PaymentStatusEnum.PROCESSING.value,
        # Also accept direct enum values
        "success": PaymentStatusEnum.SUCCESS.value,
        "failed": PaymentStatusEnum.FAILED.value,
        "pending": PaymentStatusEnum.PENDING.value,
        "processing": PaymentStatusEnum.PROCESSING.value,
    }

    mapped_status = status_mapping.get(payment_status.lower(), payment_status)

    # Find order by tracking number
    statement = select(Order).where(Order.tracking_number == tracking_number)
    order = session.exec(statement).first()

    if not order:
        return api_response(404, "Order not found", {"tracking_number": tracking_number})

    # Update payment status
    order.payment_status = mapped_status

    # If payment successful, set gateway to payfast if not already set
    if mapped_status == PaymentStatusEnum.SUCCESS.value and not order.payment_gateway:
        order.payment_gateway = "payfast"

    session.add(order)
    session.commit()
    session.refresh(order)

    return api_response(200, "Payment status updated", {
        "order_id": order.id,
        "tracking_number": order.tracking_number,
        "payment_status": order.payment_status,
        "payment_gateway": order.payment_gateway,
    })


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


# ============================================
# PAYFAST IPN (Instant Payment Notification)
# ============================================


def log_ipn_request(ipn_data: dict, error: str = None, request_info: dict = None):
    """
    Log PayFast IPN request to a file.
    Creates/appends to a daily log file: logs/ipn_log_YYYY-MM-DD.log
    """
    import os
    import json
    from datetime import datetime

    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Create filename with current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_filename = f"ipn_log_{current_date}.log"
    log_path = os.path.join(logs_dir, log_filename)

    # Prepare log entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "request_info": request_info or {},
        "ipn_data": ipn_data,
    }

    if error:
        log_entry["error"] = error
        log_entry["status"] = "ERROR"
    else:
        log_entry["status"] = "SUCCESS"

    # Append to log file
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"[{timestamp}] IPN Request - {log_entry['status']}\n")
        f.write("-" * 80 + "\n")
        f.write(json.dumps(log_entry, indent=2, default=str) + "\n")
        f.write("=" * 80 + "\n\n")


@router.post("/payfast/ipn")
async def payfast_ipn(
    session: GetSession,
    request: Request,
):
    """
    Handle PayFast IPN (Instant Payment Notification).
    Updates order payment status based on the transaction result.

    PayFast Response Codes:
    - 00: Success
    - Other codes: Failed/Declined
    """
    from sqlmodel import select
    from src.api.models.order_model.orderModel import PaymentStatusEnum

    # Collect request info for logging
    request_info = {
        "method": request.method,
        "url": str(request.url),
        "client_host": request.client.host if request.client else None,
        "headers": dict(request.headers),
    }

    ipn_data = {}

    try:
        # Parse the IPN data
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            ipn_data = await request.json()
        else:
            form = await request.form()
            ipn_data = dict(form)

        # Log the IPN data for debugging
        print(f"PayFast IPN received: {ipn_data}")

        # Extract key fields from PayFast IPN
        # TOKEN/BASKET_ID contains the order tracking number
        order_token = (
            ipn_data.get("TOKEN") or
            ipn_data.get("token") or
            ipn_data.get("BASKET_ID") or
            ipn_data.get("basket_id") or
            ipn_data.get("pp_TxnRefNo") or
            ipn_data.get("orderRefNumber")
        )

        # Response code determines success/failure
        response_code = (
            ipn_data.get("RESPONSE_CODE") or
            ipn_data.get("response_code") or
            ipn_data.get("pp_ResponseCode") or
            ipn_data.get("responseCode") or
            ""
        )

        # Response message for logging
        response_message = (
            ipn_data.get("RESPONSE_MESSAGE") or
            ipn_data.get("response_message") or
            ipn_data.get("pp_ResponseMessage") or
            ipn_data.get("responseMessage") or
            ""
        )

        if not order_token:
            error_msg = "No order token found in request"
            print(f"PayFast IPN: {error_msg}")
            log_ipn_request(ipn_data, error=error_msg, request_info=request_info)
            return {"status": "error", "message": "No order token provided"}

        # Find the order by tracking number
        statement = select(Order).where(Order.tracking_number == order_token)
        order = session.exec(statement).first()

        if not order:
            error_msg = f"Order not found for token {order_token}"
            print(f"PayFast IPN: {error_msg}")
            log_ipn_request(ipn_data, error=error_msg, request_info=request_info)
            return {"status": "error", "message": "Order not found"}

        # Determine payment status based on response code
        # PayFast uses "00" for successful transactions
        if response_code == "00":
            new_payment_status = PaymentStatusEnum.SUCCESS
            print(f"PayFast IPN: Payment SUCCESS for order {order_token}")
        elif response_code in ["", None]:
            # No response code might mean pending or processing
            new_payment_status = PaymentStatusEnum.PROCESSING
            print(f"PayFast IPN: Payment PROCESSING for order {order_token}")
        else:
            # Any other code is a failure
            new_payment_status = PaymentStatusEnum.FAILED
            print(f"PayFast IPN: Payment FAILED for order {order_token} - Code: {response_code}, Message: {response_message}")

        # Update order payment status
        order.payment_status = new_payment_status.value

        # Store the full IPN response for reference
        order.payment_response = ipn_data

        # If payment successful, also update payment gateway if not set
        if new_payment_status == PaymentStatusEnum.SUCCESS and not order.payment_gateway:
            order.payment_gateway = "payfast"

        session.add(order)
        session.commit()
        session.refresh(order)

        print(f"PayFast IPN: Order {order_token} payment status updated to {new_payment_status.value}")

        # Log successful IPN request
        log_ipn_request(ipn_data, request_info=request_info)

        # Return success to acknowledge receipt (prevents PayFast retries)
        return {
            "status": "ok",
            "order_id": order.id,
            "tracking_number": order.tracking_number,
            "payment_status": order.payment_status
        }

    except Exception as e:
        error_msg = f"Exception processing IPN: {str(e)}"
        print(f"PayFast IPN Error: {error_msg}")
        log_ipn_request(ipn_data, error=error_msg, request_info=request_info)
        # Still return ok to prevent PayFast retries
        return {"status": "ok", "error": str(e)}
