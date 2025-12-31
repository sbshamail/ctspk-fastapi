from typing import Optional, Dict, Any, Tuple, List
from decimal import Decimal
from datetime import datetime
import uuid

from sqlmodel import Session, select

from src.api.models.order_model.orderModel import Order, PaymentStatusEnum
from src.api.models.payment_model.paymentTransactionModel import (
    PaymentTransaction,
    PaymentTransactionStatus,
    PaymentGatewayType,
    PaymentFlowType,
)
from .gateway_factory import PaymentGatewayFactory


class PaymentHelper:
    """
    Static helper class for payment operations.
    Follows the same pattern as NotificationHelper and EmailHelper.
    """

    @staticmethod
    def generate_transaction_id() -> str:
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"TXN-{timestamp}-{unique_id}"

    @staticmethod
    def initiate_payment(
        session: Session,
        order_id: int,
        gateway_name: str,
        amount: Decimal,
        customer_id: Optional[int] = None,
        customer_name: Optional[str] = None,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Initiate a payment transaction.

        Returns:
            Tuple of (success, result_data)
            result_data contains: transaction_id, redirect_url or payment_data, error_message
        """
        try:
            # Get gateway
            gateway = PaymentGatewayFactory.get_gateway(gateway_name)
            if not gateway:
                return False, {"error": f"Payment gateway '{gateway_name}' is not available"}

            # Get order
            order = session.get(Order, order_id)
            if not order:
                return False, {"error": "Order not found"}

            # Generate transaction ID
            transaction_id = PaymentHelper.generate_transaction_id()

            # Determine gateway type enum value
            try:
                gateway_type = PaymentGatewayType(gateway_name.lower()).value
            except ValueError:
                gateway_type = gateway_name.lower()

            # Determine flow type
            try:
                flow_type = PaymentFlowType(gateway.flow_type).value
            except ValueError:
                flow_type = gateway.flow_type

            # Create payment transaction record
            transaction = PaymentTransaction(
                transaction_id=transaction_id,
                order_id=order_id,
                gateway_type=gateway_type,
                flow_type=flow_type,
                amount=amount,
                currency=gateway.currency,
                status=PaymentTransactionStatus.INITIATED.value,
                customer_id=customer_id,
                customer_name=customer_name or order.customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone or order.customer_contact,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.add(transaction)
            session.flush()

            # Initiate payment with gateway
            result = gateway.initiate_payment(
                transaction_id=transaction_id,
                amount=amount,
                order_id=order_id,
                customer_name=transaction.customer_name or "",
                customer_email=transaction.customer_email or "",
                customer_phone=transaction.customer_phone or "",
                description=description,
            )

            if result.success:
                # Update transaction with gateway response
                transaction.gateway_transaction_id = result.gateway_transaction_id
                transaction.redirect_url = result.redirect_url
                transaction.gateway_request = result.payment_data
                transaction.status = PaymentTransactionStatus.PENDING.value

                # Update order payment status
                order.payment_status = PaymentStatusEnum.PROCESSING.value
                order.payment_gateway = gateway_name

                session.add(transaction)
                session.add(order)
                session.commit()

                return True, {
                    "transaction_id": transaction_id,
                    "gateway_transaction_id": result.gateway_transaction_id,
                    "redirect_url": result.redirect_url,
                    "payment_data": result.payment_data,
                    "flow_type": gateway.flow_type,
                }
            else:
                # Update transaction with error
                transaction.status = PaymentTransactionStatus.FAILED.value
                transaction.error_code = result.error_code
                transaction.error_message = result.error_message
                session.add(transaction)
                session.commit()

                return False, {
                    "transaction_id": transaction_id,
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                }

        except Exception as e:
            session.rollback()
            return False, {"error": str(e)}

    @staticmethod
    def verify_payment(
        session: Session,
        transaction_id: str,
        gateway_transaction_id: Optional[str] = None,
        verification_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify a payment with the gateway.

        Returns:
            Tuple of (success, result_data)
        """
        try:
            # Get transaction
            statement = select(PaymentTransaction).where(
                PaymentTransaction.transaction_id == transaction_id
            )
            transaction = session.exec(statement).first()

            if not transaction:
                return False, {"error": "Transaction not found"}

            # Get gateway
            gateway = PaymentGatewayFactory.get_gateway(transaction.gateway_type)
            if not gateway:
                return False, {"error": "Gateway not available"}

            # Verify with gateway
            result = gateway.verify_payment(
                transaction_id=transaction_id,
                gateway_transaction_id=gateway_transaction_id
                or transaction.gateway_transaction_id,
                verification_data=verification_data,
            )

            # Update transaction
            transaction.gateway_response = result.gateway_response
            transaction.updated_at = datetime.utcnow()

            if result.success:
                transaction.status = PaymentTransactionStatus.COMPLETED.value
                transaction.completed_at = datetime.utcnow()
                transaction.gateway_transaction_id = (
                    result.gateway_transaction_id or transaction.gateway_transaction_id
                )

                # Update order
                order = session.get(Order, transaction.order_id)
                if order:
                    order.payment_status = PaymentStatusEnum.SUCCESS.value
                    session.add(order)
            else:
                if result.status == "pending":
                    transaction.status = PaymentTransactionStatus.PENDING.value
                else:
                    transaction.status = PaymentTransactionStatus.FAILED.value
                    transaction.error_code = result.error_code
                    transaction.error_message = result.error_message

                    # Update order
                    order = session.get(Order, transaction.order_id)
                    if order:
                        order.payment_status = PaymentStatusEnum.FAILED.value
                        session.add(order)

            session.add(transaction)
            session.commit()

            return result.success, {
                "transaction_id": transaction_id,
                "status": transaction.status,
                "gateway_transaction_id": result.gateway_transaction_id,
                "amount": str(result.amount) if result.amount else None,
            }

        except Exception as e:
            session.rollback()
            return False, {"error": str(e)}

    @staticmethod
    def process_callback(
        session: Session, gateway_name: str, callback_data: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Process gateway callback/redirect.

        Returns:
            Tuple of (success, transaction_id, result_data)
        """
        try:
            gateway = PaymentGatewayFactory.get_gateway(gateway_name)
            if not gateway:
                return False, "", {"error": "Gateway not available"}

            # Process callback
            success, transaction_id, parsed_data = gateway.process_callback(callback_data)

            if transaction_id:
                # Verify the payment
                verify_success, verify_result = PaymentHelper.verify_payment(
                    session, transaction_id, verification_data=parsed_data
                )

                return verify_success, transaction_id, {
                    **verify_result,
                    "callback_data": parsed_data,
                }

            return False, "", {"error": "Could not extract transaction ID"}

        except Exception as e:
            return False, "", {"error": str(e)}

    @staticmethod
    def process_webhook(
        session: Session,
        gateway_name: str,
        payload: bytes,
        headers: Dict[str, str],
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Process gateway webhook/IPN.

        Returns:
            Tuple of (success, result_data)
        """
        try:
            gateway = PaymentGatewayFactory.get_gateway(gateway_name)
            if not gateway:
                return False, {"error": "Gateway not available"}

            # Verify webhook
            result = gateway.verify_webhook(payload, headers)

            if not result.valid:
                return False, {"error": result.error_message}

            if result.transaction_id:
                # Get transaction
                statement = select(PaymentTransaction).where(
                    PaymentTransaction.transaction_id == result.transaction_id
                )
                transaction = session.exec(statement).first()

                if transaction:
                    # Update webhook data
                    transaction.webhook_received = True
                    transaction.webhook_data = result.parsed_data
                    transaction.webhook_received_at = datetime.utcnow()
                    transaction.updated_at = datetime.utcnow()

                    # Update status based on webhook
                    if result.status == "completed":
                        transaction.status = PaymentTransactionStatus.COMPLETED.value
                        transaction.completed_at = datetime.utcnow()

                        # Update order
                        order = session.get(Order, transaction.order_id)
                        if order:
                            order.payment_status = PaymentStatusEnum.SUCCESS.value
                            session.add(order)

                    elif result.status == "failed":
                        transaction.status = PaymentTransactionStatus.FAILED.value

                        order = session.get(Order, transaction.order_id)
                        if order:
                            order.payment_status = PaymentStatusEnum.FAILED.value
                            session.add(order)

                    session.add(transaction)
                    session.commit()

                    return True, {
                        "transaction_id": result.transaction_id,
                        "status": transaction.status,
                    }

            return True, {"message": "Webhook processed"}

        except Exception as e:
            session.rollback()
            return False, {"error": str(e)}

    @staticmethod
    def refund_payment(
        session: Session,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a refund.

        Returns:
            Tuple of (success, result_data)
        """
        try:
            # Get transaction
            statement = select(PaymentTransaction).where(
                PaymentTransaction.transaction_id == transaction_id
            )
            transaction = session.exec(statement).first()

            if not transaction:
                return False, {"error": "Transaction not found"}

            if transaction.status != PaymentTransactionStatus.COMPLETED.value:
                return False, {"error": "Can only refund completed transactions"}

            # Get gateway
            gateway = PaymentGatewayFactory.get_gateway(transaction.gateway_type)
            if not gateway:
                return False, {"error": "Gateway not available"}

            if not gateway.supports_refund:
                return False, {"error": "Gateway does not support refunds"}

            refund_amount = amount or transaction.amount

            if not gateway.supports_partial_refund and amount and amount < transaction.amount:
                return False, {"error": "Gateway does not support partial refunds"}

            # Check if already refunded
            max_refundable = transaction.amount - transaction.refunded_amount
            if refund_amount > max_refundable:
                return False, {"error": f"Maximum refundable amount is {max_refundable}"}

            # Process refund
            result = gateway.refund(
                transaction_id=transaction_id,
                gateway_transaction_id=transaction.gateway_transaction_id or "",
                amount=refund_amount,
                reason=reason,
            )

            if result.success:
                transaction.refunded_amount += refund_amount
                transaction.updated_at = datetime.utcnow()

                if transaction.refunded_amount >= transaction.amount:
                    transaction.status = PaymentTransactionStatus.REFUNDED.value
                else:
                    transaction.status = PaymentTransactionStatus.PARTIALLY_REFUNDED.value

                # Update order
                order = session.get(Order, transaction.order_id)
                if order:
                    order.payment_status = PaymentStatusEnum.REVERSAL.value
                    session.add(order)

                session.add(transaction)
                session.commit()

                return True, {
                    "refund_id": result.refund_id,
                    "refunded_amount": str(refund_amount),
                    "total_refunded": str(transaction.refunded_amount),
                    "status": transaction.status,
                }
            else:
                return False, {
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                }

        except Exception as e:
            session.rollback()
            return False, {"error": str(e)}

    @staticmethod
    def get_transaction_status(
        session: Session, transaction_id: str
    ) -> Dict[str, Any]:
        """Get transaction status"""
        statement = select(PaymentTransaction).where(
            PaymentTransaction.transaction_id == transaction_id
        )
        transaction = session.exec(statement).first()

        if not transaction:
            return {"error": "Transaction not found"}

        return {
            "transaction_id": transaction.transaction_id,
            "order_id": transaction.order_id,
            "gateway": transaction.gateway_type,
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "status": transaction.status,
            "refunded_amount": str(transaction.refunded_amount),
            "created_at": transaction.created_at.isoformat(),
            "completed_at": transaction.completed_at.isoformat()
            if transaction.completed_at
            else None,
        }

    @staticmethod
    def get_order_transactions(session: Session, order_id: int) -> List[Dict[str, Any]]:
        """Get all transactions for an order"""
        statement = (
            select(PaymentTransaction)
            .where(PaymentTransaction.order_id == order_id)
            .order_by(PaymentTransaction.created_at.desc())
        )

        transactions = session.exec(statement).all()

        return [
            {
                "transaction_id": t.transaction_id,
                "gateway": t.gateway_type,
                "amount": str(t.amount),
                "currency": t.currency,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ]


# Convenience functions (following EmailHelper pattern)
def initiate_payment(
    session: Session, order_id: int, gateway_name: str, amount: Decimal, **kwargs
):
    """Convenience function for initiating payment"""
    return PaymentHelper.initiate_payment(
        session, order_id, gateway_name, amount, **kwargs
    )


def verify_payment(session: Session, transaction_id: str, **kwargs):
    """Convenience function for verifying payment"""
    return PaymentHelper.verify_payment(session, transaction_id, **kwargs)


def refund_payment(
    session: Session,
    transaction_id: str,
    amount: Optional[Decimal] = None,
    reason: Optional[str] = None,
):
    """Convenience function for refunding payment"""
    return PaymentHelper.refund_payment(session, transaction_id, amount, reason)
