import json

from fastapi import APIRouter, HTTPException

from app.config import client as openai_client
from app.database import ingredient_collection
from app.models.error_models import ErrorResponse
from app.models.recipe.ingredient_info_models import IngredientRequest, Ingredient, IngredientResponse
from app.utils.image_utils import download_and_encode_image

router = APIRouter()


@router.post("/recipe/ingredient-info", tags=["Recipe"], response_model=IngredientResponse,
             responses={400: {"model": ErrorResponse}})
async def get_ingredient_info(request: IngredientRequest):
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
        ingredient_prompt = f"""'{request.ingredient_name}'에 대한 상세한 정보를 JSON 형식으로 생성해주세요. 다음 구조를 따라주세요:

        {{
          "name": "{request.ingredient_name}",
          "description": "식재료에 대한 상세한 설명. 다음 내용을 포함해주세요:
            1. 식재료의 일반적인 특징 (외형, 맛, 향 등)
            2. 영양학적 가치 (주요 영양소, 건강상의 이점 등)
            3. 일반적인 조리법이나 사용 방법
            4. 보관 방법 및 유통기한
            5. 구매 시 주의사항이나 선별 방법",
          "category": "식재료의 대분류 (예: 채소, 과일, 육류, 해산물, 유제품, 곡물 등)",
          "season": "제철 시기 또는 '연중' (해당되는 경우)",
          "alternatives": ["대체 가능한 식재료 목록 (2-3개)"]
        }}

        주의사항:
        1. 설명은 정확하고 객관적이어야 하며, 과학적 근거가 있는 정보를 제공해야 합니다.
        2. 각 항목에 대해 구체적이고 유용한 정보를 제공해주세요.
        3. 반드시 유효한 JSON 형식으로만 응답해주세요. 추가 설명이나 주석은 불필요합니다.
        """

        ingredient_response = openai_client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 식품영양학과 요리 전문가입니다. 다양한 식재료에 대한 깊이 있는 지식을 바탕으로, 정확하고 유용한 정보를 제공합니다."},
                {"role": "user", "content": ingredient_prompt}
            ]
        )

        ingredient_json = json.loads(ingredient_response.choices[0].message.content)
        ingredient = Ingredient(**ingredient_json)

        image_prompt = f"""Create a high-quality, photorealistic image of {ingredient.name} with the following specifications:

        1. Subject: A fresh, pristine {ingredient.name} in its most commonly found or used form.
        2. Setting: Place the ingredient in a context that suggests its culinary use or natural environment.
        3. Lighting: Use bright, even lighting to clearly show the ingredient's color, texture, and details.
        4. Composition: 
           - Main focus should be on the {ingredient.name}, occupying about 70% of the frame.
           - Include some complementary elements that hint at its use or origin (e.g., a cutting board, knife, or typical accompanying ingredients).
        5. Style: Clean, professional food photography style, as if for a high-end cookbook or culinary magazine.
        6. Detail: Capture the unique characteristics described: {ingredient.description[:100]}...

        Additional notes:
        - If applicable, show the ingredient both whole and cut to reveal its interior.
        - Avoid any text or labels in the image.
        - Ensure the image is appetizing and showcases the ingredient in its best light.
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
