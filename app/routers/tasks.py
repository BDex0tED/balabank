# app/routers/tasks.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel
from typing import List
from decimal import Decimal

from app.database import get_session
from app.models import User, Task, TaskStatus, UserRole, Transaction
from app.core.deps import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])

class TaskCreate(BaseModel):
    title: str
    description: str
    reward: Decimal
    child_id: int

@router.post("/", response_model=Task)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Only parents can create tasks")

    child = await session.get(User, task_data.child_id)
    
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    
    if child.family_id != current_user.family_id:
        raise HTTPException(status_code=403, detail="This is not your family member!")

    if child.role != UserRole.CHILD:
        raise HTTPException(
            status_code=400, 
            detail="Tasks can only be assigned to children! You cannot assign tasks to yourself or other parents."
        )

    new_task = Task(
        title=task_data.title,
        description=task_data.description,
        reward=task_data.reward,
        child_id=child.id,
        creator_id=current_user.id,
        status=TaskStatus.NEW
    )
    
    session.add(new_task)
    await session.commit()
    await session.refresh(new_task)
    return new_task

@router.get("/", response_model=List[Task])
async def get_tasks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role == UserRole.CHILD:
        stmt = select(Task).where(Task.child_id == current_user.id)
    else:
        stmt = select(Task).where(Task.creator_id == current_user.id)
    result = await session.exec(stmt)
    return result.all()

@router.post("/{task_id}/submit")
async def submit_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.child_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your task!")
    task.status = TaskStatus.WAITING_APPROVAL
    session.add(task)
    await session.commit()
    return {"message": "Task submitted for approval"}

@router.post("/{task_id}/approve")
async def approve_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Only parents can approve")

    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == TaskStatus.DONE:
        raise HTTPException(status_code=400, detail="Already paid!")

    if current_user.balance < task.reward:
        raise HTTPException(status_code=400, detail="Not enough money on balance!")
        
    current_user.balance -= task.reward
    
    child = await session.get(User, task.child_id)
    child.balance += task.reward
    
    task.status = TaskStatus.DONE
    
    transaction = Transaction(
        amount=task.reward,
        sender_id=current_user.id,
        receiver_id=child.id,
        description=f"Payment for task: {task.title}"
    )
    
    session.add(current_user)
    session.add(child)
    session.add(task)
    session.add(transaction)
    
    await session.commit()
    
    return {"message": f"Task approved! Paid {task.reward} to {child.name}"}

@router.post("/{task_id}/reject")
async def reject_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Only parents can reject")

    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = TaskStatus.NEW 
    
    session.add(task)
    await session.commit()
    
    return {"message": "Task rejected and sent back to child."}