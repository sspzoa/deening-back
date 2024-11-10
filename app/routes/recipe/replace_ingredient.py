import logging

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.config import client as openai_client
from app.database import recipe_collection
from app.models.recipe.replace_ingredient_models import ReplaceIngredientRequest, ReplaceIngredientResponse

router = APIRouter()


@router.post("/recipe/replace-ingredient", tags=["Recipe"], response_model=ReplaceIngredientResponse)
async def replace_ingredient(request: ReplaceIngredientRequest):
    """
    레시피의 특정 재료에 대한 대체 재료를 추천하고 맛의 변화를 설명합니다.
    """
    try:
        # 데이터베이스에서 레시피 검색
        recipe = await recipe_collection.find_one({"_id": ObjectId(request.recipe_id)})
        if not recipe:
            raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다.")

        # 재료 존재 여부 확인
        ingredient_exists = any(ing["name"] == request.ingredient_name for ing in recipe["ingredients"])
        if not ingredient_exists:
            raise HTTPException(status_code=404, detail="지정된 재료를 레시피에서 찾을 수 없습니다.")

        # 대체 재료 및 맛 변화 설명을 위한 프롬프트
        prompt = f"""다음 레시피의 '{request.ingredient_name}'를 대체할 수 있는 가장 적합한 재료와 그로 인한 맛의 변화를 설명해주세요.

        레시피: {recipe['name']}
        레시피 설명: {recipe['description']}
        
        대체할 재료: {request.ingredient_name}
        
        다음 사항을 고려해주세요:
        1. 원재료와 비슷한 맛과 식감을 제공할 수 있는 재료
        2. 레시피의 전반적인 특성을 해치지 않는 재료
        3. 조리 방법이 크게 달라지지 않는 재료
        
        다음 JSON 형식으로 답변해주세요:
        {{
            "replaced_ingredient": "대체 재료 이름",
            "taste_change_description": "맛의 변화에 대한 설명"
        }}
        """

        response = openai_client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 요리 전문가로서 재료 대체에 대한 전문적인 지식을 가지고 있습니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        result = response.choices[0].message.content.strip()
        result_json = eval(result)  # JSON 파싱

        return ReplaceIngredientResponse(
            replaced_ingredient=result_json["replaced_ingredient"],
            taste_change_description=result_json["taste_change_description"]
        )

    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
