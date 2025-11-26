from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel

from app.routers import users, auth, family, tasks, loans, ask
from app.database import engine

from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield

app = FastAPI(
    title="BalaBank API",
    lifespan=lifespan
)

origins = [
    "*",                          
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        
    allow_credentials=True,       
    allow_methods=["*"],          
    allow_headers=["*"],          
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(family.router)
app.include_router(tasks.router)
app.include_router(loans.router)
app.include_router(ask.router)



@app.get("/")
async def root():
    return {"message": "Yokoso watashi no soul society"}