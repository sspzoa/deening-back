import logging

from bson import ObjectId
from fastapi import HTTPException, APIRouter

from app.database import preference_collection
from app.models.error_models import ErrorResponse
from app.models.preference.preference_models import (
    GetKeywordsResponse, Keyword, Preference,
    AddKeywordRequest, AddKeywordResponse, DeleteKeywordResponse,
    UpdateKeywordRequest, UpdateKeywordResponse
)

router = APIRouter()


@router.get("/preferences/keywords", tags=["Preference"], response_model=GetKeywordsResponse)
async def get_keywords():
    """
    저장된 모든 키워드 목록을 반환합니다.
    키워드가 없을 경우 빈 배열을 반환합니다.
    """
    try:
        keywords = await preference_collection.find().to_list(length=None)

        # 키워드가 없을 경우 빈 Preference 객체 반환
        if not keywords:
            return GetKeywordsResponse(preference=Preference(keywords=[]))

        # ObjectId를 문자열로 변환하여 키워드 목록 생성
        keyword_list = [Keyword(id=str(keyword["_id"]), name=keyword["name"], type=keyword["type"])
                        for keyword in keywords]

        return GetKeywordsResponse(preference=Preference(keywords=keyword_list))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/preferences/keywords", tags=["Preference"],
            responses={400: {"model": ErrorResponse}},
            response_model=AddKeywordResponse)
async def add_keyword(request: AddKeywordRequest):
    """
    새로운 키워드를 추가합니다. 이미 존재하는 키워드는 추가되지 않습니다.
    """
    try:
        # 이미 존재하는 키워드인지 확인
        existing_keyword = await preference_collection.find_one(
            {"name": request.name, "type": request.type}
        )

        if existing_keyword:
            raise HTTPException(status_code=400, detail="이미 존재하는 키워드입니다.")

        # 새로운 키워드 추가
        await preference_collection.insert_one(request.model_dump())
        return {"message": "키워드가 성공적으로 추가되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/preferences/keyword/{keyword_id}", tags=["Preference"],
               response_model=DeleteKeywordResponse,
               responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def delete_keyword(keyword_id: str):
    """
    주어진 ID로 키워드를 삭제합니다.
    """
    try:
        object_id = ObjectId(keyword_id)
    except:
        raise HTTPException(status_code=404, detail="유효하지 않은 키워드 ID입니다.")

    try:
        result = await preference_collection.delete_one({"_id": object_id})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="해당 ID의 키워드를 찾을 수 없습니다.")

        return {"message": "키워드가 성공적으로 삭제되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/preferences/keyword/{keyword_id}", tags=["Preference"],
              response_model=UpdateKeywordResponse,
              responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def update_keyword(keyword_id: str, request: UpdateKeywordRequest):
    """
    주어진 ID로 키워드를 수정합니다.
    """
    try:
        object_id = ObjectId(keyword_id)
    except:
        raise HTTPException(status_code=404, detail="유효하지 않은 키워드 ID입니다.")

    try:
        # 키워드 존재 여부 확인
        existing_keyword = await preference_collection.find_one({"_id": object_id})
        if not existing_keyword:
            raise HTTPException(status_code=404, detail="해당 ID의 키워드를 찾을 수 없습니다.")

        # 업데이트할 필드 준비
        update_data = {k: v for k, v in request.model_dump().items() if v is not None}

        # 키워드 업데이트
        result = await preference_collection.update_one(
            {"_id": object_id},
            {"$set": update_data}
        )

        if result.modified_count == 0:
            return {"message": "변경된 내용이 없습니다."}

        return {"message": "키워드가 성공적으로 수정되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
