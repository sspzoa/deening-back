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
    레시피의 특정 재료에 대한 대체 재료를 추천합니다.
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

        # 대체 재료 추천을 위한 프롬프트
        prompt = f"""다음 레시피의 '{request.ingredient_name}'를 대체할 수 있는 가장 적합한 재료 하나만 추천해주세요.

        레시피: {recipe['name']}
        레시피 설명: {recipe['description']}
        
        대체할 재료: {request.ingredient_name}
        
        다음 사항을 고려해주세요:
        1. 원재료와 비슷한 맛과 식감을 제공할 수 있는 재료
        2. 레시피의 전반적인 특성을 해치지 않는 재료
        3. 조리 방법이 크게 달라지지 않는 재료
        
        재료 이름만 답변해주세요.
        """

        response = openai_client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 요리 전문가로서 재료 대체에 대한 전문적인 지식을 가지고 있습니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        replaced_ingredient = response.choices[0].message.content.strip()
        return ReplaceIngredientResponse(replaced_ingredient=replaced_ingredient)

    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
