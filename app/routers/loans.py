from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel
from datetime import datetime
from typing import List
from decimal import Decimal

from app.database import get_session
from app.models import User, Loan, LoanStatus, UserRole, Transaction
from app.core.deps import get_current_user

router = APIRouter(prefix="/loans", tags=["Loans (Microcredit)"])

class LoanRequest(BaseModel):
    amount: Decimal
    description: str

class LoanApproveRequest(BaseModel):
    interest_rate: Decimal  
    due_date: datetime    

@router.post("/", response_model=Loan)
async def request_loan(
    data: LoanRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != UserRole.CHILD:
        raise HTTPException(status_code=403, detail="Only children can request loans")

    new_loan = Loan(
        amount=data.amount,
        description=data.description,
        borrower_id=current_user.id,
        interest_rate=0.0,
        total_to_pay=data.amount,
        status=LoanStatus.REQUESTED,
        lender_id=None
    )
    
    session.add(new_loan)
    await session.commit()
    await session.refresh(new_loan)
    return new_loan

@router.get("/", response_model=List[Loan])
async def get_loans(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role == UserRole.CHILD:
        stmt = select(Loan).where(Loan.borrower_id == current_user.id)
    else:
        stmt = (
            select(Loan)
            .join(User, Loan.borrower_id == User.id)
            .where(User.family_id == current_user.family_id)
        )
        
    result = await session.exec(stmt)
    return result.all()

@router.post("/{loan_id}/approve")
async def approve_loan(
    loan_id: int,
    approval_data: LoanApproveRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Only parents approve loans")

    loan = await session.get(Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    borrower = await session.get(User, loan.borrower_id)
    if borrower.family_id != current_user.family_id:
        raise HTTPException(status_code=403, detail="This is not your family's loan request")

    if loan.status != LoanStatus.REQUESTED:
        raise HTTPException(status_code=400, detail="Loan is not in requested state")

    if current_user.balance < loan.amount:
        raise HTTPException(status_code=400, detail="Not enough money")

    clean_due_date = approval_data.due_date.replace(tzinfo=None)

    total = loan.amount + (loan.amount * approval_data.interest_rate / 100)
    
    loan.status = LoanStatus.ACTIVE
    loan.interest_rate = approval_data.interest_rate
    loan.total_to_pay = total
    loan.due_date = clean_due_date 
    loan.lender_id = current_user.id 

    current_user.balance -= loan.amount
    borrower.balance += loan.amount

    transaction = Transaction(
        amount=loan.amount,
        sender_id=current_user.id,
        receiver_id=borrower.id,
        description=f"Loan issued: {loan.description}"
    )

    session.add(loan)
    session.add(current_user)
    session.add(borrower)
    session.add(transaction)
    
    await session.commit()
    await session.refresh(loan)
    
    return loan

@router.post("/{loan_id}/repay")
async def repay_loan(
    loan_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    loan = await session.get(Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    if loan.borrower_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your loan")
        
    if loan.status != LoanStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Loan is not active")

    if current_user.balance < loan.total_to_pay:
        raise HTTPException(status_code=400, detail="Not enough money to repay")

    if not loan.lender_id:
        raise HTTPException(status_code=500, detail="Lender information missing")
        
    lender = await session.get(User, loan.lender_id)
    if not lender:
        raise HTTPException(status_code=404, detail="Lender account not found")

    current_user.balance -= loan.total_to_pay
    lender.balance += loan.total_to_pay
    
    loan.status = LoanStatus.PAID
    
    transaction = Transaction(
        amount=loan.total_to_pay,
        sender_id=current_user.id,
        receiver_id=lender.id,
        description=f"Loan repaid: {loan.description}"
    )

    session.add(loan)
    session.add(current_user)
    session.add(lender)
    session.add(transaction)
    
    await session.commit()
    
    return {"message": "Loan repaid successfully!"}

@router.post("/{loan_id}/reject")
async def reject_loan(
    loan_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Only parents can reject loans")

    loan = await session.get(Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    borrower = await session.get(User, loan.borrower_id)
    if borrower.family_id != current_user.family_id:
        raise HTTPException(status_code=403, detail="Not your family loan")

    if loan.status != LoanStatus.REQUESTED:
        raise HTTPException(status_code=400, detail="Loan is not in requested state")

    loan.status = LoanStatus.REJECTED
    
    session.add(loan)
    await session.commit()
    
    return {"message": "Loan request rejected"}