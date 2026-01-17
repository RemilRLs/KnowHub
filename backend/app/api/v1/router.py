from fastapi import APIRouter
from app.api.v1.routes import health, ingest, embed, generate, collections


api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(embed.router, prefix="/ingest", tags=["embedding"])
api_router.include_router(generate.router, prefix="/generate", tags=["generation"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])