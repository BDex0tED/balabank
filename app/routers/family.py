# app/routers/family.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel
import uuid

from app.database import get_session
from app.models import User, Family, UserRole
from app.core.deps import get_current_user

router = APIRouter(prefix="/families", tags=["Family Logic"])

# DTO для создания семьи
class FamilyCreateRequest(BaseModel):
    name: str

# DTO для вступления
class JoinFamilyRequest(BaseModel):
    invite_code: str
    role: UserRole  # Юзер сам выбирает: PARENT или CHILD

# 1. СОЗДАТЬ СЕМЬЮ (Тот, кто создает - автоматически становится РОДИТЕЛЕМ)
@router.post("/create")
async def create_family(
    data: FamilyCreateRequest,
    current_user: User = Depends(get_current_user), # Берем юзера из токена
    session: AsyncSession = Depends(get_session)
):
    if current_user.family_id is not None:
        raise HTTPException(status_code=400, detail="You are already in a family!")

    # Генерируем код
    code = str(uuid.uuid4())[:6]
    
    # Создаем семью
    new_family = Family(name=data.name, invite_code=code)
    session.add(new_family)
    await session.commit()
    await session.refresh(new_family)

    # Обновляем юзера (он становится Батей/Мамой этой семьи)
    current_user.family_id = new_family.id
    current_user.role = UserRole.PARENT
    current_user.balance = 10000.0 # Бонус за создание семьи
    
    session.add(current_user)
    await session.commit()

    return {"message": "Family created", "invite_code": code}

# 2. ВСТУПИТЬ В СЕМЬЮ (Как говорил Амир: по коду и указывая роль)
@router.post("/join")
async def join_family(
    data: JoinFamilyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.family_id is not None:
        raise HTTPException(status_code=400, detail="You are already in a family!")

    # Ищем семью по коду
    stmt = select(Family).where(Family.invite_code == data.invite_code)
    family = (await session.exec(stmt)).first()
    
    if not family:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    # Валидация возраста для роли (опционально, но логично)
    if data.role == UserRole.PARENT and current_user.age < 18:
         raise HTTPException(status_code=400, detail="Parents must be 18+")

    # Обновляем юзера
    current_user.family_id = family.id
    current_user.role = data.role
    
    # Если зашел как родитель - дадим стартовый баланс, если ребенок - 0
    if data.role == UserRole.PARENT:
        current_user.balance = 10000.0
    else:
        current_user.balance = 0.0

    session.add(current_user)
    await session.commit()

    return {"message": f"Joined family {family.name} as {data.role}"}

# ... (твои импорты в начале файла family.py) ...
# Убедись, что импортировал Family из models:
# from ..models import User, Family, UserRole

# 1. DTO для красивого ответа (чтобы не отдавать лишнее, типа ID)
class FamilyResponse(BaseModel):
    name: str
    invite_code: str
    role_in_family: UserRole

# 2. НОВЫЙ ЭНДПОИНТ: Получить инфу о моей семье
@router.get("/me", response_model=FamilyResponse)
async def get_my_family_info(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Если юзер беспризорник
    if current_user.family_id is None:
        raise HTTPException(
            status_code=400, 
            detail="You are not in a family yet."
        )

    # Ищем семью по ID, который прописан у юзера
    family = await session.get(Family, current_user.family_id)
    
    if not family:
        # Этого быть не должно, но на всякий случай
        raise HTTPException(status_code=404, detail="Family not found")

    return {
        "name": family.name,
        "invite_code": family.invite_code,
        "role_in_family": current_user.role
    }