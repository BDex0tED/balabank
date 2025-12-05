import uuid
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel, field_validator 
import re 

from app.core.deps import get_current_user
from app.database import get_session
from app.models import Family, User, UserRole
from app.core.security import get_password_hash, verify_password, create_access_token

from decimal import Decimal

router = APIRouter(prefix="/auth", tags=["Auth"])

class UserRegistration(BaseModel):
    phone_number: str 
    
    surname: str
    name: str
    paternity: str
    password: str
    age: int
    role: str
    family_name: str
    

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean_number = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        if not clean_number.isdigit():
            raise ValueError('Номер должен содержать только цифры')
        
        if len(clean_number) == 10 and clean_number.startswith("0"):
            clean_number = clean_number[1:]
            
        if len(clean_number) != 9:
            raise ValueError('Номер должен состоять из 9 цифр (код оператора + номер). Например: 555123456')
        
        return f"+996{clean_number}"

class ChildRegistration(BaseModel):
    phone_number: str 
    
    surname: str
    name: str
    paternity: str
    password: str
    age: int
    role: str
    family_id: int

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean_number = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        if not clean_number.isdigit():
            raise ValueError('Номер должен содержать только цифры')
        
        if len(clean_number) == 10 and clean_number.startswith("0"):
            clean_number = clean_number[1:]
            
        if len(clean_number) != 9:
            raise ValueError('Номер должен состоять из 9 цифр (код оператора + номер). Например: 555123456')
        
        return f"+996{clean_number}"
    


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegistration,
    session: AsyncSession = Depends(get_session)
):
    
    stmt = select(User).where(User.phone_number == data.phone_number)
    if (await session.exec(stmt)).first():
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    code = str(uuid.uuid4())[:6]
    new_family = Family(name=data.family_name, invite_code=code)

    session.add(new_family)
    await session.commit()
    await session.refresh(new_family)



    new_user = User(
        phone_number=data.phone_number,
        hashed_password=get_password_hash(data.password),
        surname=data.surname,
        name=data.name,
        paternity=data.paternity,
        age=data.age,
        balance=Decimal("10000.00"),
        role= UserRole.PARENT,
        family_id=new_family.id
    )

    session.add(new_user)
    await session.commit()
    
    return {"message": "User registered successfully"}

@router.post("/register-child", status_code=status.HTTP_201_CREATED)
async def register_child(
    data: ChildRegistration, 
    session: AsyncSession = Depends(get_session)
):
    
    stmt = select(User).where(User.phone_number == data.phone_number)
    if (await session.exec(stmt)).first():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    new_user = User(
        phone_number=data.phone_number,
        hashed_password=get_password_hash(data.password),
        surname=data.surname,
        name=data.name,
        paternity=data.paternity,
        age=data.age,
        balance=Decimal("0.00"),
        role=data.role,
        family_id=data.family_id
    )

    session.add(new_user)
    await session.commit()
    
    return {"message": "User registered successfully"}


@router.post("/login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session)
):
    input_phone = form_data.username
    
    clean = input_phone.replace(" ", "").replace("+996", "") 
    if len(clean) == 10 and clean.startswith("0"):
        clean = clean[1:]
    
    db_format_phone = f"+996{clean}"

    stmt = select(User).where(User.phone_number == db_format_phone)
    user = (await session.exec(stmt)).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect phone or password")
    
    access_token = create_access_token(data={"sub": user.phone_number})
    return {"access_token": access_token, "token_type": "bearer"}