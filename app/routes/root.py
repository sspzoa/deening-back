from fastapi import APIRouter
from starlette.responses import FileResponse

router = APIRouter()


@router.get("/")
async def root():
    """
    Landing Page
    """
    return FileResponse("app/static/index.html")
