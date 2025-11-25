# app/routers/auth.py
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel, field_validator # <-- Импортируем field_validator
import re # Библиотека для регулярных выражений (проверка шаблонов)

from ..database import get_session
from ..models import User
from ..core.security import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

class UserRegistration(BaseModel):
    # Пользователь вводит только 9 цифр (без +996)
    phone_number: str 
    
    surname: str
    name: str
    paternity: str
    password: str
    age: int

    # --- МАГИЯ ВАЛИДАЦИИ ---
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # 1. Удаляем пробелы и скобки, если юзер ввел "0 555 12 34 56"
        clean_number = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # 2. Проверяем, что остались только цифры
        if not clean_number.isdigit():
            raise ValueError('Номер должен содержать только цифры')
        
        # 3. Проверяем длину (должно быть 9 цифр, так как +996 мы добавим сами)
        # Если юзер случайно ввел с 0 в начале (0555...), простим его и уберем ноль
        if len(clean_number) == 10 and clean_number.startswith("0"):
            clean_number = clean_number[1:]
            
        if len(clean_number) != 9:
            raise ValueError('Номер должен состоять из 9 цифр (код оператора + номер). Например: 555123456')
        
        # 4. Превращаем в полный формат для базы
        return f"+996{clean_number}"

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegistration, 
    session: AsyncSession = Depends(get_session)
):
    # data.phone_number УЖЕ прошел валидацию и выглядит как "+996555123456"
    
    # 1. Проверяем уникальность
    stmt = select(User).where(User.phone_number == data.phone_number)
    if (await session.exec(stmt)).first():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # 2. Создаем юзера
    new_user = User(
        phone_number=data.phone_number,
        hashed_password=get_password_hash(data.password),
        surname=data.surname,
        name=data.name,
        paternity=data.paternity,
        age=data.age,
        balance=0.0,
        role=None,
        family_id=None
    )

    session.add(new_user)
    await session.commit()
    
    return {"message": "User registered successfully"}

# --- ЛОГИН НУЖНО ЧУТЬ ПОДПРАВИТЬ ---
@router.post("/login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session)
):
    # form_data.username - это то, что ввел юзер в поле логина.
    # Если он ввел "0555123456" или "555123456", нам нужно привести это 
    # к формату "+996...", чтобы найти в базе.
    
    input_phone = form_data.username
    
    # Мини-очистка для входа (такая же логика)
    clean = input_phone.replace(" ", "").replace("+996", "") # Если вдруг ввел с кодом
    if len(clean) == 10 and clean.startswith("0"):
        clean = clean[1:]
    
    db_format_phone = f"+996{clean}"

    # Ищем в базе
    stmt = select(User).where(User.phone_number == db_format_phone)
    user = (await session.exec(stmt)).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect phone or password")
    
    access_token = create_access_token(data={"sub": user.phone_number})
    return {"access_token": access_token, "token_type": "bearer"}