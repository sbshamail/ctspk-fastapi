# src/api/core/transaction_logger.py
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
from sqlmodel import Session, select, func, and_, or_
import uuid

from src.api.models.transactionLogModel import (
    TransactionLog, TransactionLogCreate, TransactionType, TransactionDirection
)
from src.api.models.product_model.productsModel import Product
from src.api.models.product_model.variationOptionModel import VariationOption
from src.api.models.order_model.orderModel import Order, OrderProduct
from src.api.models.usersModel import User
from src.api.models.shop_model.shopsModel import Shop

class TransactionLogger:
    """Helper class to log all transactions in the system"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def generate_reference_number(self, prefix: str = "TRN") -> str:
        """Generate unique reference number for transaction"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = uuid.uuid4().hex[:6].upper()
        return f"{prefix}-{timestamp}-{random_suffix}"
    
    def check_duplicate_transaction(self, log_data: TransactionLogCreate) -> bool:
        """Check if a similar transaction already exists (within 5 minutes)"""
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        
        conditions = [
            TransactionLog.transaction_type == log_data.transaction_type,
            TransactionLog.created_at >= five_minutes_ago
        ]
        
        if log_data.product_id:
            conditions.append(TransactionLog.product_id == log_data.product_id)
        if log_data.order_id:
            conditions.append(TransactionLog.order_id == log_data.order_id)
        if log_data.reference_number:
            conditions.append(TransactionLog.reference_number == log_data.reference_number)
        if log_data.quantity_change is not None:
            conditions.append(TransactionLog.quantity_change == log_data.quantity_change)
        
        existing = self.session.exec(
            select(TransactionLog).where(and_(*conditions))
        ).first()
        
        return existing is not None
    
    def generate_auto_notes(self, log_data: TransactionLogCreate) -> str:
        """Generate automatic notes based on transaction type and data"""
        notes_parts = []
        
        # Get entity names for better readability
        product_name = None
        if log_data.product_id:
            product = self.session.get(Product, log_data.product_id)
            if product:
                product_name = product.name
        
        order_tracking = None
        if log_data.order_id:
            order = self.session.get(Order, log_data.order_id)
            if order:
                order_tracking = order.tracking_number
        
        # Build notes based on transaction type
        if log_data.transaction_type == TransactionType.PRODUCT_CREATE:
            notes_parts.append(f"New product created")
            if product_name:
                notes_parts.append(f": {product_name}")
        
        elif log_data.transaction_type == TransactionType.PRODUCT_UPDATE:
            notes_parts.append("Product updated")
            if product_name:
                notes_parts.append(f": {product_name}")
            
            # Add price change details
            if log_data.previous_price is not None and log_data.new_price is not None:
                price_diff = log_data.new_price - log_data.previous_price
                if price_diff != 0:
                    direction = "increased" if price_diff > 0 else "decreased"
                    notes_parts.append(f", price {direction} from ${log_data.previous_price:.2f} to ${log_data.new_price:.2f}")
        
        elif log_data.transaction_type in [TransactionType.STOCK_ADDITION, TransactionType.STOCK_DEDUCTION]:
            action = "added to" if log_data.transaction_type == TransactionType.STOCK_ADDITION else "deducted from"
            notes_parts.append(f"Stock {action}")
            if product_name:
                notes_parts.append(f" {product_name}")
            
            if log_data.quantity_change is not None:
                abs_qty = abs(log_data.quantity_change)
                notes_parts.append(f": {abs_qty} units")
                
                if log_data.purchase_price is not None and log_data.transaction_type == TransactionType.STOCK_ADDITION:
                    notes_parts.append(f" at purchase price ${log_data.purchase_price:.2f}")
        
        elif log_data.transaction_type == TransactionType.ORDER_PLACED:
            notes_parts.append("Order placed")
            if order_tracking:
                notes_parts.append(f": #{order_tracking}")
        
        elif log_data.transaction_type == TransactionType.ORDER_CANCELLED:
            notes_parts.append("Order cancelled")
            if order_tracking:
                notes_parts.append(f": #{order_tracking}")
            if product_name:
                notes_parts.append(f" for {product_name}")
        
        elif log_data.transaction_type == TransactionType.ORDER_RETURNED:
            notes_parts.append("Item returned")
            if order_tracking:
                notes_parts.append(f" from order #{order_tracking}")
            if product_name:
                notes_parts.append(f": {product_name}")
        
        elif log_data.transaction_type == TransactionType.PRICE_CHANGE:
            notes_parts.append("Price changed")
            if product_name:
                notes_parts.append(f" for {product_name}")
            if log_data.previous_price is not None and log_data.new_price is not None:
                price_diff = log_data.new_price - log_data.previous_price
                direction = "increased" if price_diff > 0 else "decreased"
                notes_parts.append(f": {direction} from ${log_data.previous_price:.2f} to ${log_data.new_price:.2f}")
        
        # Add quantity change details if available
        if (log_data.previous_quantity is not None and 
            log_data.new_quantity is not None and
            log_data.previous_quantity != log_data.new_quantity):
            
            qty_change = log_data.new_quantity - log_data.previous_quantity
            if abs(qty_change) > 0:
                if len(notes_parts) > 0:
                    notes_parts.append(";")
                action = "increased" if qty_change > 0 else "decreased"
                notes_parts.append(f" stock {action} from {log_data.previous_quantity} to {log_data.new_quantity}")
        
        # Add reference numbers if available
        if log_data.reference_number:
            if len(notes_parts) > 0:
                notes_parts.append(" -")
            notes_parts.append(f" Ref: {log_data.reference_number}")
        
        if log_data.invoice_number:
            if len(notes_parts) > 0:
                notes_parts.append(",")
            notes_parts.append(f" Invoice: {log_data.invoice_number}")
        
        return "".join(notes_parts)
    
    def log_transaction(self, log_data: TransactionLogCreate, user_id: Optional[int] = None) -> TransactionLog:
        """Main method to log a transaction"""
        
        # Set user_id if not provided
        if not log_data.user_id and user_id:
            log_data.user_id = user_id
        
        # Generate reference number if not provided
        if not log_data.reference_number:
            log_data.reference_number = self.generate_reference_number()
        
        # Determine direction based on quantity change
        direction = TransactionDirection.NO_CHANGE
        if log_data.quantity_change is not None:
            if log_data.quantity_change > 0:
                direction = TransactionDirection.INCREASE
            elif log_data.quantity_change < 0:
                direction = TransactionDirection.DECREASE
        
        # Generate auto notes if not provided
        auto_notes = self.generate_auto_notes(log_data)
        
        # Check for duplicate transactions
        is_duplicate = self.check_duplicate_transaction(log_data)
        
        # Create transaction log
        transaction_log = TransactionLog(
            **log_data.model_dump(),
            direction=direction,
            auto_generated_notes=auto_notes,
            is_duplicate=is_duplicate,
            is_system_generated=not log_data.notes,  # If notes provided, it's manual
            requires_review=is_duplicate  # Flag duplicates for review
        )
        
        # Save to database
        self.session.add(transaction_log)
        self.session.commit()
        self.session.refresh(transaction_log)
        
        # Highlight duplicate in logs
        if is_duplicate:
            print(f"⚠️ DUPLICATE TRANSACTION DETECTED: {transaction_log.id} - {auto_notes}")
        
        return transaction_log
    
    # Specific helper methods for common transactions
    
    def log_product_creation(self, product: Product, user_id: int, notes: Optional[str] = None) -> TransactionLog:
        """Log product creation"""
        log_data = TransactionLogCreate(
            transaction_type=TransactionType.PRODUCT_CREATE,
            product_id=product.id,
            shop_id=product.shop_id,
            user_id=user_id,
            purchase_price=product.purchase_price,
            unit_price=product.price,
            sale_price=product.sale_price,
            previous_quantity=0,
            new_quantity=product.quantity,
            quantity_change=product.quantity,
            notes=notes
        )
        return self.log_transaction(log_data, user_id)
    
    def log_stock_addition(self, product: Product = None, product_id: int = None, quantity: int = None,
                          purchase_price: float = None, user_id: int = None, shop_id: int = None,
                          notes: Optional[str] = None, reference_number: Optional[str] = None,
                          variation_option_id: Optional[int] = None, previous_quantity: Optional[int] = None,
                          new_quantity: Optional[int] = None) -> TransactionLog:
        """Log stock addition with purchase price"""
        if product:
            product_id = product.id
            shop_id = product.shop_id
        elif product_id:
            product = self.session.get(Product, product_id)

        log_data = TransactionLogCreate(
            transaction_type=TransactionType.STOCK_ADDITION,
            product_id=product_id,
            shop_id=shop_id,
            user_id=user_id,
            quantity_change=quantity,
            purchase_price=purchase_price,
            unit_price=product.price if product else None,
            sale_price=product.sale_price if product else None,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            reference_number=reference_number,
            notes=notes,
            variation_option_id=variation_option_id
        )
        return self.log_transaction(log_data, user_id)
    
    def log_stock_deduction(self, product: Product = None, product_id: int = None, quantity: int = None,
                           unit_price: float = None, sale_price: Optional[float] = None,
                           user_id: int = None, shop_id: int = None, notes: Optional[str] = None,
                           order_id: Optional[int] = None, order_product_id: Optional[int] = None,
                           variation_option_id: Optional[int] = None,
                           previous_quantity: Optional[int] = None, new_quantity: Optional[int] = None,
                           subtotal: Optional[float] = None, discount: Optional[float] = None,
                           tax: Optional[float] = None, total: Optional[float] = None) -> TransactionLog:
        """Log stock deduction (for orders, returns, etc.)"""
        if product:
            product_id = product.id
            shop_id = product.shop_id
            if unit_price is None:
                unit_price = product.price
            if sale_price is None:
                sale_price = product.sale_price
        elif product_id:
            product = self.session.get(Product, product_id)

        log_data = TransactionLogCreate(
            transaction_type=TransactionType.STOCK_DEDUCTION,
            product_id=product_id,
            shop_id=shop_id,
            user_id=user_id,
            order_id=order_id,
            order_product_id=order_product_id,
            quantity_change=-quantity,  # Negative for deduction
            purchase_price=None,  # No purchase price for deductions
            unit_price=unit_price,
            sale_price=sale_price,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            notes=notes,
            variation_option_id=variation_option_id,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total=total
        )
        return self.log_transaction(log_data, user_id)
    
    def log_price_change(self, product: Product = None, product_id: int = None,
                        previous_price: float = None, new_price: float = None,
                        previous_sale_price: Optional[float] = None, new_sale_price: Optional[float] = None,
                        user_id: int = None, shop_id: int = None, notes: Optional[str] = None,
                        variation_option_id: Optional[int] = None) -> TransactionLog:
        """Log price change"""
        if product:
            product_id = product.id
            shop_id = product.shop_id
        elif product_id:
            product = self.session.get(Product, product_id)

        log_data = TransactionLogCreate(
            transaction_type=TransactionType.PRICE_CHANGE,
            product_id=product_id,
            shop_id=shop_id,
            user_id=user_id,
            previous_price=previous_price,
            new_price=new_price,
            unit_price=new_price,
            sale_price=new_sale_price if new_sale_price is not None else (product.sale_price if product else None),
            notes=notes,
            variation_option_id=variation_option_id
        )
        return self.log_transaction(log_data, user_id)
    
    def log_order_placed(self, order: Order, user_id: int, notes: Optional[str] = None) -> TransactionLog:
        """Log order placement"""
        log_data = TransactionLogCreate(
            transaction_type=TransactionType.ORDER_PLACED,
            order_id=order.id,
            shop_id=None,  # Will be logged per product
            user_id=user_id,
            subtotal=order.amount,
            discount=order.discount,
            tax=order.sales_tax,
            total=order.total,
            reference_number=order.tracking_number,
            notes=notes
        )
        return self.log_transaction(log_data, user_id)
    
    def log_order_cancelled(self, order_id: int, product_id: int, quantity: int,
                           unit_price: float, sale_price: Optional[float],
                           user_id: int, shop_id: int, notes: Optional[str] = None) -> TransactionLog:
        """Log order cancellation (stock restoration)"""
        log_data = TransactionLogCreate(
            transaction_type=TransactionType.ORDER_CANCELLED,
            order_id=order_id,
            product_id=product_id,
            shop_id=shop_id,
            user_id=user_id,
            quantity_change=quantity,  # Positive for restoration
            unit_price=unit_price,
            sale_price=sale_price,
            notes=notes
        )
        return self.log_transaction(log_data, user_id)
    
    def log_product_update(self, product: Product, previous_data: Dict[str, Any],
                          user_id: int, notes: Optional[str] = None) -> List[TransactionLog]:
        """Log product update with changes detection"""
        logs = []
        
        # Check for price changes
        if 'price' in previous_data and previous_data['price'] != product.price:
            logs.append(self.log_price_change(
                product_id=product.id,
                previous_price=previous_data['price'],
                new_price=product.price,
                user_id=user_id,
                shop_id=product.shop_id,
                notes=notes or "Price updated"
            ))
        
        # Check for sale price changes
        if ('sale_price' in previous_data and 
            previous_data['sale_price'] != product.sale_price):
            # Log as price change with specific note
            sale_note = f"Sale price updated: {previous_data.get('sale_price', 'N/A')} → {product.sale_price}"
            logs.append(self.log_price_change(
                product_id=product.id,
                previous_price=previous_data.get('sale_price') or product.price,
                new_price=product.sale_price or product.price,
                user_id=user_id,
                shop_id=product.shop_id,
                notes=notes or sale_note
            ))
        
        # Check for quantity changes (not from stock additions/deductions)
        if ('quantity' in previous_data and 
            previous_data['quantity'] != product.quantity):
            qty_change = product.quantity - previous_data['quantity']
            if qty_change != 0:
                transaction_type = (TransactionType.STOCK_ADDITION if qty_change > 0 
                                  else TransactionType.STOCK_DEDUCTION)
                
                log_data = TransactionLogCreate(
                    transaction_type=transaction_type,
                    product_id=product.id,
                    shop_id=product.shop_id,
                    user_id=user_id,
                    quantity_change=qty_change,
                    previous_quantity=previous_data['quantity'],
                    new_quantity=product.quantity,
                    unit_price=product.price,
                    sale_price=product.sale_price,
                    notes=notes or f"Quantity adjusted: {qty_change:+d} units"
                )
                logs.append(self.log_transaction(log_data, user_id))
        
        return logs
    
    def get_transaction_history(self, filters: Dict[str, Any] = None, 
                               limit: int = 100, offset: int = 0) -> List[TransactionLog]:
        """Get transaction history with filters"""
        query = select(TransactionLog)
        
        if filters:
            conditions = []
            for key, value in filters.items():
                if hasattr(TransactionLog, key):
                    field = getattr(TransactionLog, key)
                    if isinstance(value, list):
                        conditions.append(field.in_(value))
                    else:
                        conditions.append(field == value)
            
            if conditions:
                query = query.where(and_(*conditions))
        
        query = query.order_by(TransactionLog.transaction_date.desc())
        query = query.offset(offset).limit(limit)
        
        return self.session.exec(query).all()
    
    def get_product_transaction_history(self, product_id: int, limit: int = 50) -> List[TransactionLog]:
        """Get transaction history for a specific product"""
        return self.get_transaction_history(
            filters={'product_id': product_id},
            limit=limit
        )
    
    def get_daily_transaction_summary(self, date: datetime = None) -> Dict[str, Any]:
        """Get daily transaction summary"""
        if not date:
            date = datetime.utcnow().date()
        
        start_date = datetime.combine(date, datetime.min.time())
        end_date = datetime.combine(date, datetime.max.time())
        
        # Get all transactions for the day
        transactions = self.session.exec(
            select(TransactionLog).where(
                and_(
                    TransactionLog.created_at >= start_date,
                    TransactionLog.created_at <= end_date
                )
            )
        ).all()
        
        # Calculate summaries
        summary = {
            'date': date,
            'total_transactions': len(transactions),
            'transactions_by_type': {},
            'stock_additions': 0,
            'stock_deductions': 0,
            'total_stock_change': 0,
            'financial_summary': {
                'total_sales': 0,
                'total_purchases': 0,
                'net_change': 0
            }
        }
        
        for transaction in transactions:
            # Count by type
            t_type = transaction.transaction_type
            summary['transactions_by_type'][t_type] = summary['transactions_by_type'].get(t_type, 0) + 1
            
            # Track stock changes
            if transaction.quantity_change:
                if transaction.direction == TransactionDirection.INCREASE:
                    summary['stock_additions'] += transaction.quantity_change
                elif transaction.direction == TransactionDirection.DECREASE:
                    summary['stock_deductions'] += abs(transaction.quantity_change)
                summary['total_stock_change'] += transaction.quantity_change
            
            # Track financials
            if transaction.transaction_type == TransactionType.ORDER_PLACED:
                if transaction.total:
                    summary['financial_summary']['total_sales'] += transaction.total
            
            if (transaction.transaction_type == TransactionType.STOCK_ADDITION and 
                transaction.purchase_price and transaction.quantity_change):
                purchase_amount = transaction.purchase_price * transaction.quantity_change
                summary['financial_summary']['total_purchases'] += purchase_amount
        
        summary['financial_summary']['net_change'] = (
            summary['financial_summary']['total_sales'] - 
            summary['financial_summary']['total_purchases']
        )
        
        return summary