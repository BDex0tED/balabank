# app/models.py
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum

class UserRole(str, Enum):
    PARENT = "parent"
    CHILD = "child"

class Family(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    invite_code: str = Field(unique=True, index=True)
    members: List["User"] = Relationship(back_populates="family")

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # --- ИЗМЕНЕНИЕ: ВМЕСТО USERNAME ТЕПЕРЬ ТЕЛЕФОН ---
    phone_number: str = Field(unique=True, index=True) 
    
    hashed_password: str
    
    surname: str  
    name: str
    paternity: str
    age: int
    
    role: Optional[UserRole] = Field(default=None)
    family_id: Optional[int] = Field(default=None, foreign_key="family.id")
    balance: float = Field(default=0.0)
    
    family: Optional[Family] = Relationship(back_populates="members")