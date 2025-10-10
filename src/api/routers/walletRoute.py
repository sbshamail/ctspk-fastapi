# src/api/routes/walletRoute.py
from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import select
from datetime import datetime
from src.api.core.response import api_response, raiseExceptions
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
)
from src.api.models.returnModel import (
    WalletTransaction, WalletTransactionRead,
    UserWallet, UserWalletRead,
    TransferToBankRequest
)

router = APIRouter(prefix="/wallet", tags=["Wallet"])


# ✅ GET MY WALLET BALANCE
@router.get("/balance")
def get_my_wallet(
    session: GetSession,
    user=requireSignin
):
    user_wallet = session.exec(
        select(UserWallet).where(UserWallet.user_id == user.id)
    ).first()
    
    if not user_wallet:
        user_wallet = UserWallet(user_id=user.id, balance=0.0)
        session.add(user_wallet)
        session.commit()
        session.refresh(user_wallet)
    
    return api_response(200, "Wallet balance retrieved", UserWalletRead.model_validate(user_wallet))


# ✅ GET MY WALLET TRANSACTIONS
@router.get("/transactions", response_model=list[WalletTransactionRead])
def get_my_transactions(
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
        searchFields=["description"],
        Model=WalletTransaction,
        Schema=WalletTransactionRead,
    )


# ✅ TRANSFER TO BANK
@router.post("/transfer-to-bank")
def transfer_to_bank(
    request: TransferToBankRequest,
    session: GetSession,
    user=requireSignin,
    background_tasks: BackgroundTasks = None,
):
    # Get user wallet
    user_wallet = session.exec(
        select(UserWallet).where(UserWallet.user_id == user.id)
    ).first()
    
    if not user_wallet or user_wallet.balance <= 0:
        return api_response(400, "Insufficient wallet balance")

    # Check if amount is valid
    if request.amount <= 0 or request.amount > user_wallet.balance:
        return api_response(400, "Invalid transfer amount")

    # Get eligible refund transactions (15 days old)
    eligible_transactions = session.exec(
        select(WalletTransaction).where(
            WalletTransaction.user_id == user.id,
            WalletTransaction.transaction_type == "credit",
            WalletTransaction.is_refund == True,
            WalletTransaction.transfer_eligible_at <= datetime.utcnow(),
            WalletTransaction.transferred_to_bank == False
        )
    ).all()

    total_eligible = sum(t.amount for t in eligible_transactions)
    
    if request.amount > total_eligible:
        return api_response(400, f"Only ${total_eligible} is eligible for transfer (15-day holding period)")

    # Process transfer
    try:
        # Update wallet
        user_wallet.balance -= request.amount
        user_wallet.total_debited += request.amount

        # Mark transactions as transferred
        amount_to_transfer = request.amount
        for transaction in eligible_transactions:
            if amount_to_transfer <= 0:
                break
            
            if amount_to_transfer >= transaction.amount:
                transaction.transferred_to_bank = True
                transaction.transferred_at = datetime.utcnow()
                amount_to_transfer -= transaction.amount
            else:
                # Partial transfer (create new transaction for remaining)
                remaining_amount = transaction.amount - amount_to_transfer
                
                # Update current transaction
                transaction.amount = amount_to_transfer
                transaction.balance_after = user_wallet.balance
                transaction.transferred_to_bank = True
                transaction.transferred_at = datetime.utcnow()
                
                # Create new transaction for remaining amount
                new_transaction = WalletTransaction(
                    user_id=user.id,
                    amount=remaining_amount,
                    transaction_type="credit",
                    balance_after=user_wallet.balance + remaining_amount,
                    description=f"Remaining from transfer of refund",
                    is_refund=True,
                    transfer_eligible_at=transaction.transfer_eligible_at,
                    return_request_id=transaction.return_request_id
                )
                session.add(new_transaction)
                amount_to_transfer = 0

        # Create debit transaction record
        debit_transaction = WalletTransaction(
            user_id=user.id,
            amount=request.amount,
            transaction_type="debit",
            balance_after=user_wallet.balance,
            description=f"Transfer to bank account #{request.bank_account_id}",
            is_refund=False
        )
        session.add(debit_transaction)

        session.commit()

        # Process bank transfer in background
        if background_tasks:
            background_tasks.add_task(process_bank_transfer, user.id, request.amount, request.bank_account_id)

        return api_response(200, f"${request.amount} transfer initiated successfully")

    except Exception as e:
        session.rollback()
        return api_response(500, f"Transfer failed: {str(e)}")


# ✅ GET ELIGIBLE TRANSFER AMOUNT
@router.get("/eligible-transfer-amount")
def get_eligible_transfer_amount(
    session: GetSession,
    user=requireSignin
):
    # Calculate amount that is eligible for transfer (15 days old)
    eligible_transactions = session.exec(
        select(WalletTransaction).where(
            WalletTransaction.user_id == user.id,
            WalletTransaction.transaction_type == "credit",
            WalletTransaction.is_refund == True,
            WalletTransaction.transfer_eligible_at <= datetime.utcnow(),
            WalletTransaction.transferred_to_bank == False
        )
    ).all()

    total_eligible = sum(t.amount for t in eligible_transactions)
    
    return api_response(200, "Eligible transfer amount", {
        "eligible_amount": total_eligible,
        "transaction_count": len(eligible_transactions)
    })


def process_bank_transfer(user_id: int, amount: float, bank_account_id: int):
    """Background task to process actual bank transfer"""
    # Integrate with your payment gateway/bank API here
    print(f"Processing bank transfer of ${amount} to account #{bank_account_id} for user {user_id}")
    
    # Example integration:
    # bank_api.transfer(amount, bank_account_id)
    # Update transfer status in database if needed


# ✅ SCHEDULED TASK: CHECK TRANSFER ELIGIBILITY
def check_transfer_eligibility():
    """Scheduled task to update transfer eligibility"""
    from src.api.core.database import get_db_session
    
    with get_db_session() as session:
        # Find refund transactions that just became eligible
        newly_eligible = session.exec(
            select(WalletTransaction).where(
                WalletTransaction.transaction_type == "credit",
                WalletTransaction.is_refund == True,
                WalletTransaction.transfer_eligible_at <= datetime.utcnow(),
                WalletTransaction.transferred_to_bank == False
            )
        ).all()
        
        # You could send notifications to users here
        for transaction in newly_eligible:
            print(f"Transaction #{transaction.id} is now eligible for bank transfer")
            
            # Send notification to user
            # notify_user_about_eligible_transfer(transaction.user_id, transaction.amount)