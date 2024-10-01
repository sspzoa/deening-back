from fastapi import APIRouter
from app.models.ping_models import PingResponse

router = APIRouter()

@router.get("/ping", response_model=PingResponse)
async def ping():
    return {"message": "pong"}