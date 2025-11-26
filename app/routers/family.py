from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
import uuid

from app.database import get_session
from app.models import User, Family, UserRole, FamilyRequest, RequestStatus
from app.core.deps import get_current_user

router = APIRouter(prefix="/families", tags=["Family Logic"])

class FamilyCreateRequest(BaseModel):
    name: str

class JoinFamilyRequest(BaseModel):
    invite_code: str

class RequestResponse(BaseModel):
    request_id: int
    user_full_name: str
    user_age: int
    user_phone: str
    status: RequestStatus 

class MyRequestStatus(BaseModel):
    family_name: str
    status: RequestStatus
    created_at: str

class ApproveRequest(BaseModel):
    role: UserRole 

class FamilyResponse(BaseModel):
    name: str
    invite_code: str
    role_in_family: Optional[UserRole] = None


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

@router.post("/request-join")
async def request_join_family(
    data: JoinFamilyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.family_id is not None:
        raise HTTPException(status_code=400, detail="You are already in a family!")

    stmt = select(Family).where(Family.invite_code == data.invite_code)
    family = (await session.exec(stmt)).first()
    
    if not family:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    stmt_req = select(FamilyRequest).where(
        FamilyRequest.user_id == current_user.id,
        FamilyRequest.family_id == family.id,
        FamilyRequest.status == RequestStatus.PENDING
    )
    if (await session.exec(stmt_req)).first():
        raise HTTPException(status_code=400, detail="You already have a pending request to this family")

    new_request = FamilyRequest(
        user_id=current_user.id, 
        family_id=family.id,
        status=RequestStatus.PENDING 
    )
    session.add(new_request)
    await session.commit()

    return {"message": f"Request sent to family {family.name}. Wait for approval."}

@router.get("/my-requests", response_model=List[MyRequestStatus])
async def get_my_requests(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(FamilyRequest, Family).join(Family).where(FamilyRequest.user_id == current_user.id)
    results = await session.exec(stmt)
    
    response = []
    for req, fam in results:
        response.append(MyRequestStatus(
            family_name=fam.name,
            status=req.status,
            created_at=str(req.created_at)
        ))
    return response

@router.get("/requests", response_model=List[RequestResponse])
async def get_family_requests(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != UserRole.PARENT or not current_user.family_id:
        raise HTTPException(status_code=403, detail="Only parents can view requests")

    stmt = (
        select(FamilyRequest, User)
        .join(User)
        .where(FamilyRequest.family_id == current_user.family_id)
        .where(FamilyRequest.status == RequestStatus.PENDING)
    )
    results = await session.exec(stmt)
    
    response_list = []
    for req, user in results:
        full_name = f"{user.surname} {user.name}"
        response_list.append(RequestResponse(
            request_id=req.id,
            user_full_name=full_name,
            user_age=user.age,
            user_phone=user.phone_number,
            status=req.status
        ))
    
    return response_list

@router.post("/requests/{request_id}/approve")
async def approve_request(
    request_id: int,
    data: ApproveRequest, 
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Only parents can approve")

    req = await session.get(FamilyRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if req.family_id != current_user.family_id:
        raise HTTPException(status_code=403, detail="Not your family request")

    target_user = await session.get(User, req.user_id)
    
    target_user.family_id = req.family_id
    target_user.role = data.role 
    
    if data.role == UserRole.PARENT:
        target_user.balance = 10000.0
    else:
        target_user.balance = 0.0

    req.status = RequestStatus.APPROVED

    session.add(req)
    session.add(target_user)
    await session.commit()

    return {"message": f"User accepted as {data.role}"}

@router.post("/requests/{request_id}/reject")
async def reject_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Only parents can reject")

    req = await session.get(FamilyRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if req.family_id != current_user.family_id:
        raise HTTPException(status_code=403, detail="Not your family request")

    req.status = RequestStatus.REJECTED
    
    session.add(req)
    await session.commit()

    return {"message": "Request rejected"}

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