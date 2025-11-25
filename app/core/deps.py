# app/core/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..database import get_session
from ..models import User
from .security import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    session: AsyncSession = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Достаем телефон из поля 'sub'
        phone_number: str = payload.get("sub") 
        if phone_number is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Ищем в базе по phone_number
    statement = select(User).where(User.phone_number == phone_number)
    result = await session.exec(statement)
    user = result.first()
    
    if user is None:
        raise credentials_exception
        
    return user