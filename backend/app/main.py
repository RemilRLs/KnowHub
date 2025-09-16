from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.logging import init_logging

app = FastAPI(title="KnowHub API", version="0.1.0")

@app.on_event("startup")
async def startup_event():
    init_logging()

app.include_router(api_router, prefix="/api/v1")