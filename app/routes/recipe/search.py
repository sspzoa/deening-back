from bson.regex import Regex
from fastapi import APIRouter, HTTPException
from pymongo import ASCENDING

from app.database import recipe_collection
from app.models.recipe.search_models import SearchResponse, RecipeSimple

router = APIRouter()


@router.get("/recipe/search", tags=["Recipe"], response_model=SearchResponse)
async def search_recipes(query: str):
    """
    주어진 검색어로 레시피를 검색합니다.
    검색은 레시피 이름과 설명을 대상으로 수행됩니다.

    Args:
        query (str): 검색할 키워드

    Returns:
        SearchResponse: 검색 결과 목록
    """
    try:
        # 검색어가 비어있는 경우 처리
        if not query.strip():
            raise HTTPException(status_code=400, detail="검색어를 입력해주세요.")

        # 대소문자 구분 없이 검색하기 위한 정규식 패턴 생성
        search_pattern = Regex(f".*{query}.*", "i")

        # 이름 또는 설명에 검색어가 포함된 레시피 검색
        search_results = await recipe_collection.find({
            "$or": [
                {"name": search_pattern},
                {"description": search_pattern}
            ]
        }).sort("name", ASCENDING).to_list(length=None)

        # 검색 결과를 RecipeSimple 모델로 변환
        simple_results = [
            RecipeSimple(
                id=str(recipe["_id"]),
                name=recipe["name"],
                image_base64=recipe.get("image_base64", "")  # Base64 이미지 사용
            )
            for recipe in search_results
        ]

        return SearchResponse(search_results=simple_results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")
