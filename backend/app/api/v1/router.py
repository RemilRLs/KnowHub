from fastapi import APIRouter
from app.api.v1.routes import health, ingest, embed


api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(embed.router, prefix="/ingest", tags=["embedding"])