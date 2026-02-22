from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, health, tasks

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Secure Task Management API — DevSecOps Pipeline Reference",
)

# INTENTIONAL: Permissive CORS for ZAP scanner demonstration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(tasks.router)
