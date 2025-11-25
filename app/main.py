from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel

from app.routers import users, auth, family
from app.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield

app = FastAPI(
    title="BalaBank API",
    lifespan=lifespan
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(family.router)

@app.get("/")
async def root():
    return {"message": "Welcome to BalaBank Soul Society"}