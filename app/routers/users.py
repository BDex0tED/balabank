from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from ..database import get_session
from ..models import User
from ..core.deps import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/family", response_model=List[User])
async def read_my_family(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.family_id is None:
        return [current_user]

    # Если семья есть, ищем остальных
    statement = select(User).where(User.family_id == current_user.family_id)
    result = await session.exec(statement)
    return result.all()