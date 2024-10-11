from fastapi import APIRouter
from starlette.responses import FileResponse

router = APIRouter()


@router.get("/", include_in_schema=False)
async def root():
    """
    Landing Page
    """
    return FileResponse("app/static/index.html")
