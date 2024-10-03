from fastapi import APIRouter, HTTPException
from app.models.recipe.ingredient_models import IngredientRequest, Ingredient, IngredientResponse
from pydantic import BaseModel
from app.config import client
import json

router = APIRouter()

class ErrorResponse(BaseModel):
    error: str

@router.post("/ingredient", tags=["Recipe"], response_model=IngredientResponse, responses={400: {"model": ErrorResponse}})
async def get_ingredient_info(request: IngredientRequest):
    """
    식재료 정보와 이미지를 생성합니다.
    """
    try:
        # 식재료 정보 생성 프롬프트
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
        
        주의: 반드시 다른 텍스트 없이 유효한 JSON 형식으로만 응답해주세요.
        """

        # 식재료 정보 생성
        ingredient_response = client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 영양학 전문가입니다. 주어진 식재료에 대한 상세한 정보를 JSON 형식으로 제공합니다."},
                {"role": "user", "content": ingredient_prompt}
            ]
        )

        ingredient_json = json.loads(ingredient_response.choices[0].message.content)
        ingredient = Ingredient(**ingredient_json)

        # 이미지 생성 프롬프트
        image_prompt = f"""A high-quality, detailed photo of {ingredient.name}, as described:

        - Category: {ingredient.category}
        - Description: {ingredient.description}

        The image should clearly show the ingredient in its natural or commonly found form. 
        Ensure the lighting is bright and even, showcasing the ingredient's texture and color.
        If applicable, include some context that hints at its culinary uses or storage method.
        """

        # DALL-E를 사용한 이미지 생성
        image_response = client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        # 이미지 URL 가져오기
        image_url = image_response.data[0].url

        return IngredientResponse(ingredient=ingredient, image_url=image_url)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="생성된 식재료 정보를 JSON으로 파싱할 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))