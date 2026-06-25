from fastapi import APIRouter

from backend.app.api.routers import auth, reports, tasks, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tasks.router)
api_router.include_router(reports.router)
