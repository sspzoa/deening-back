from itertools import groupby

from bson import ObjectId
from fastapi import HTTPException, APIRouter

from app.database import refrigerator_collection
from app.models.error_models import ErrorResponse
from app.models.refrigerator.refrigerator_models import GetIngredientsResponse, Ingredient, IngredientCategory, \
    Refrigerator, AddIngredientResponse, AddIngredientRequest, DeleteIngredientResponse

router = APIRouter()


@router.get("/refrigerator/ingredients", tags=["Refrigerator"], response_model=GetIngredientsResponse)
async def get_ingredients():
    """
    냉장고에 있는 모든 재료의 리스트를 카테고리별로 묶어 반환합니다.
    재료가 없을 경우 빈 배열을 반환합니다.
    """
    try:
        ingredients = await refrigerator_collection.find().to_list(length=None)

        # 재료가 없을 경우 빈 Refrigerator 객체 반환
        if not ingredients:
            return GetIngredientsResponse(refrigerator=Refrigerator(categories=[]))

        # 카테고리별로 정렬
        sorted_ingredients = sorted(ingredients, key=lambda x: x["category"])

        # 카테고리별로 그룹화
        grouped_ingredients = []
        for category, items in groupby(sorted_ingredients, key=lambda x: x["category"]):
            category_ingredients = [Ingredient(id=str(item["_id"]), **item) for item in items]
            grouped_ingredients.append(IngredientCategory(category=category, ingredients=category_ingredients))

        refrigerator = Refrigerator(categories=grouped_ingredients)
        return GetIngredientsResponse(refrigerator=refrigerator)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/refrigerator/ingredients", tags=["Refrigerator"], responses={400: {"model": ErrorResponse}},
            response_model=AddIngredientResponse)
async def add_ingredients(request: AddIngredientRequest):
    """
    냉장고에 여러 재료를 추가합니다. 이미 존재하는 재료의 경우 양을 더합니다.
    """
    try:
        for ingredient in request.ingredients:
            # 기존 재료 찾기
            existing_ingredient = await refrigerator_collection.find_one(
                {"name": ingredient.name, "category": ingredient.category})

            if existing_ingredient:
                # 이미 존재하는 재료라면 양을 더함
                new_amount = existing_ingredient["amount"] + ingredient.amount
                await refrigerator_collection.update_one(
                    {"name": ingredient.name, "category": ingredient.category},
                    {"$set": {"amount": new_amount}}
                )
            else:
                # 새로운 재료라면 추가
                await refrigerator_collection.insert_one(ingredient.dict())

        return {"message": "재료가 성공적으로 추가되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/refrigerator/ingredient/{ingredient_id}", tags=["Refrigerator"],
               response_model=DeleteIngredientResponse,
               responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def delete_ingredient(ingredient_id: str):
    """
    주어진 ID로 냉장고에서 재료를 삭제합니다.
    """
    try:
        # ObjectId로 변환
        object_id = ObjectId(ingredient_id)
    except:
        raise HTTPException(status_code=404, detail="유효하지 않은 재료 ID입니다.")

    try:
        # 재료 삭제
        result = await refrigerator_collection.delete_one({"_id": object_id})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="해당 ID의 재료를 찾을 수 없습니다.")

        return {"message": "재료가 성공적으로 삭제되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
