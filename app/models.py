from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Numeric

class UserRole(str, Enum):
    PARENT = "parent"
    CHILD = "child"

class TaskStatus(str, Enum):
    NEW = "new"
    WAITING_APPROVAL = "waiting"
    DONE = "done"
    REJECTED = "rejected"

class LoanStatus(str, Enum):
    REQUESTED = "requested"
    ACTIVE = "active"
    PAID = "paid"
    REJECTED = "rejected"
    
class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class FamilyRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    family_id: int = Field(foreign_key="family.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    status: RequestStatus = Field(default=RequestStatus.PENDING)
    
    user: "User" = Relationship(back_populates="requests")
    family: "Family" = Relationship(back_populates="requests")

class Family(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    invite_code: str = Field(unique=True, index=True)
    
    members: List["User"] = Relationship(back_populates="family")
    requests: List["FamilyRequest"] = Relationship(back_populates="family")

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone_number: str = Field(unique=True, index=True)
    hashed_password: str
    
    surname: str  
    name: str
    paternity: str
    age: int
    
    role: Optional[UserRole] = Field(default=None)
    family_id: Optional[int] = Field(default=None, foreign_key="family.id")
    
    balance: Decimal = Field(default=Decimal("0.00"), sa_column=Column(Numeric(10, 2)))
    
    family: Optional[Family] = Relationship(back_populates="members")
    assigned_tasks: List["Task"] = Relationship(back_populates="child")
    requests: List["FamilyRequest"] = Relationship(back_populates="user")

    borrowed_loans: List["Loan"] = Relationship(
        back_populates="borrower",
        sa_relationship_kwargs={"foreign_keys": "Loan.borrower_id"}
    )
    lent_loans: List["Loan"] = Relationship(
        back_populates="lender",
        sa_relationship_kwargs={"foreign_keys": "Loan.lender_id"}
    )

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    
    reward: Decimal = Field(default=Decimal("0.00"), sa_column=Column(Numeric(10, 2)))
    
    status: TaskStatus = Field(default=TaskStatus.NEW)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    child_id: int = Field(foreign_key="user.id")
    child: User = Relationship(back_populates="assigned_tasks")
    creator_id: int 

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2)))
    
    description: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sender_id: int
    receiver_id: int

class Loan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2)))
    interest_rate: Decimal = Field(sa_column=Column(Numeric(5, 2))) 
    total_to_pay: Decimal = Field(sa_column=Column(Numeric(10, 2)))
    
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = Field(default=None)
    status: LoanStatus = Field(default=LoanStatus.REQUESTED)
    
    borrower_id: int = Field(foreign_key="user.id")
    borrower: User = Relationship(
        back_populates="borrowed_loans",
        sa_relationship_kwargs={"foreign_keys": "[Loan.borrower_id]"}
    )

    lender_id: Optional[int] = Field(default=None, foreign_key="user.id")
    lender: Optional[User] = Relationship(
        back_populates="lent_loans",
        sa_relationship_kwargs={"foreign_keys": "[Loan.lender_id]"}
    )