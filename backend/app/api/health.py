from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.core.redis import redis_client
from app.db.session import asyncSessionLocal

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/health/ready")
async def readiness():
    try:
        async with asyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

        await redis_client.ping()

        return {
            "status": "ready",
            "database": "ok",
            "redis": "ok"
            }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service dependencies are not ready") from e