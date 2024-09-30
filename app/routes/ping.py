from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class PingResponse(BaseModel):
    message: str

@router.get("/ping", response_model=PingResponse)
async def ping():
    return {"message": "pong"}