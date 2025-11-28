from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel, field_validator
from typing import List, Optional
import uuid

from app.database import get_session
from app.models import User, Family, UserRole
from app.core.deps import get_current_user
from app.core.security import get_password_hash 

router = APIRouter(prefix="/families", tags=["Family Logic"])


class FamilyCreateRequest(BaseModel):
    name: str

class JoinFamilyRequest(BaseModel):
    invite_code: str
    role: UserRole # Юзер сам выбирает роль при входе по коду

class FamilyResponse(BaseModel):
    name: str
    invite_code: str
    role_in_family: Optional[UserRole] = None

class ChildRegistrationRequest(BaseModel):
    phone_number: str 
    surname: str
    name: str
    paternity: str
    password: str
    age: int

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean_number = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not clean_number.isdigit():
            raise ValueError('Номер должен содержать только цифры')
        if len(clean_number) == 10 and clean_number.startswith("0"):
            clean_number = clean_number[1:]
        if len(clean_number) != 9:
            raise ValueError('Номер должен состоять из 9 цифр')
        return f"+996{clean_number}"


@router.post("/create")
async def create_family(
    data: FamilyCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.family_id is not None:
        raise HTTPException(status_code=400, detail="You are already in a family!")

    code = str(uuid.uuid4())[:6]
    new_family = Family(name=data.name, invite_code=code)
    
    session.add(new_family)
    await session.commit()
    await session.refresh(new_family)

    current_user.family_id = new_family.id
    current_user.role = UserRole.PARENT
    current_user.balance = 10000.0
    
    session.add(current_user)
    await session.commit()

    return {"message": "Family created", "invite_code": code}

@router.post("/join")
async def join_family(
    data: JoinFamilyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.family_id is not None:
        raise HTTPException(status_code=400, detail="You are already in a family!")

    # Ищем семью
    stmt = select(Family).where(Family.invite_code == data.invite_code)
    family = (await session.exec(stmt)).first()
    
    if not family:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    # Простая защита: Родитель должен быть совершеннолетним
    if data.role == UserRole.PARENT and current_user.age < 18:
         raise HTTPException(status_code=400, detail="Parents must be 18+")

    # Обновляем юзера
    current_user.family_id = family.id
    current_user.role = data.role
    
    # Стартовый бонус для родителей
    if data.role == UserRole.PARENT:
        current_user.balance = 10000.0
    else:
        current_user.balance = 0.0

    session.add(current_user)
    await session.commit()

    return {"message": f"Joined family {family.name} as {data.role}"}

@router.post("/add-child")
async def add_child_account(
    data: ChildRegistrationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Only parents can add children directly")
    
    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="Create a family first!")

    stmt = select(User).where(User.phone_number == data.phone_number)
    if (await session.exec(stmt)).first():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    new_child = User(
        phone_number=data.phone_number,
        hashed_password=get_password_hash(data.password), 
        surname=data.surname,
        name=data.name,
        paternity=data.paternity,
        age=data.age,
        balance=0.0,
        role=UserRole.CHILD,          
        family_id=current_user.family_id
    )

    session.add(new_child)
    await session.commit()

    return {"message": f"Child {data.name} added to family successfully!"}

@router.get("/me", response_model=FamilyResponse)
async def get_my_family_info(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.family_id is None:
        raise HTTPException(status_code=400, detail="You are not in a family yet.")

    family = await session.get(Family, current_user.family_id)
    if not family:
        raise HTTPException(status_code=404, detail="Family not found")

    return {
        "name": family.name,
        "invite_code": family.invite_code,
        "role_in_family": current_user.role
    }