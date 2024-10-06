import json

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import client as openai_client
from app.database import ingredient_collection
from app.models.recipe.ingredient_models import IngredientRequest, Ingredient, IngredientResponse
from app.utils.image_utils import download_and_encode_image

router = APIRouter()

class ErrorResponse(BaseModel):
    error: str

@router.post("/ingredient", tags=["Recipe"], response_model=IngredientResponse,
             responses={400: {"model": ErrorResponse}})
async def get_or_create_ingredient(request: IngredientRequest):
    """
    식재료 이름으로 검색하여 정보를 반환하거나, 없으면 새로 생성합니다.
    """
    try:
        # 데이터베이스에서 재료 검색
        ingredient_data = await ingredient_collection.find_one({"name": request.ingredient_name})

        if ingredient_data:
            # 이미 존재하는 재료 정보 반환
            image_base64 = ingredient_data.pop('image_base64', None)
            ingredient_id = str(ingredient_data.pop('_id'))
            ingredient = Ingredient(**ingredient_data)
            return IngredientResponse(ingredient=ingredient, image_base64=image_base64, id=ingredient_id)

        # 재료 정보가 없으면 새로 생성
        ingredient_prompt = f"""제공된 식재료에 대한 정보를 JSON 형식으로 생성해주세요. 다음 구조를 따라주세요:

        {{
          "name": "식재료 이름",
          "description": "식재료에 대한 간단한 설명",
          "category": "식재료 카테고리",
          "nutritional_info": {{
            "calories": 100g당 칼로리(정수),
            "protein": 단백질(g),
            "carbohydrates": 탄수화물(g),
            "fat": 지방(g),
            "fiber": 식이섬유(g),
            "vitamins": "주요 비타민",
            "minerals": "주요 미네랄"
          }},
          "storage_tips": "보관 방법",
          "culinary_uses": ["요리법1", "요리법2", "요리법3"]
        }}

        식재료 이름: {request.ingredient_name}
        
        주의: 반드시 다른 텍스트나 코드블록 없이 유효한 JSON 형식으로만 응답해주세요.
        """

        ingredient_response = openai_client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 영양학 전문가입니다. 주어진 식재료에 대한 상세한 정보를 JSON 형식으로 제공합니다."},
                {"role": "user", "content": ingredient_prompt}
            ]
        )

        ingredient_json = json.loads(ingredient_response.choices[0].message.content)
        ingredient = Ingredient(**ingredient_json)

        image_prompt = f"""A high-quality, detailed photo of {ingredient.name}, as described:

        - Category: {ingredient.category}
        - Description: {ingredient.description}

        The image should clearly show the ingredient in its natural or commonly found form. 
        Ensure the lighting is bright and even, showcasing the ingredient's texture and color.
        If applicable, include some context that hints at its culinary uses or storage method.
        """

        image_response = openai_client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = image_response.data[0].url
        image_base64 = 'data:image/png;base64,' + download_and_encode_image(image_url)  # 이미지 다운로드 및 Base64 인코딩

        ingredient_dict = ingredient.model_dump()
        ingredient_dict['image_base64'] = image_base64  # URL 대신 Base64 인코딩된 이미지 저장
        result = await ingredient_collection.insert_one(ingredient_dict)
        ingredient_id = str(result.inserted_id)

        return IngredientResponse(ingredient=ingredient, image_base64=image_base64, id=ingredient_id)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="생성된 식재료 정보를 JSON으로 파싱할 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/ingredient/{ingredient_id}", tags=["Recipe"], response_model=IngredientResponse,
            responses={404: {"model": ErrorResponse}})
async def get_ingredient_by_id(ingredient_id: str):
    """
    주어진 ID에 대한 식재료 정보를 반환합니다.
    """
    try:
        ingredient_data = await ingredient_collection.find_one({"_id": ObjectId(ingredient_id)})
        if not ingredient_data:
            raise HTTPException(status_code=404, detail="식재료 정보를 찾을 수 없습니다.")

        image_base64 = ingredient_data.pop('image_base64', None)
        ingredient_id = str(ingredient_data.pop('_id'))
        ingredient = Ingredient(**ingredient_data)
        return IngredientResponse(ingredient=ingredient, image_base64=image_base64, id=ingredient_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))