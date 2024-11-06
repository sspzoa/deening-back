import json
import logging
import re

from fastapi import APIRouter, HTTPException

from app.config import client as openai_client
from app.database import recipe_collection, refrigerator_collection, preference_collection
from app.models.error_models import ErrorResponse
from app.models.recipe.recipe_models import Recipe, RecipeRequest, RecipeResponse
from app.utils.image_utils import download_and_encode_image

router = APIRouter()


@router.post("/recipe", tags=["Recipe"], response_model=RecipeResponse, responses={400: {"model": ErrorResponse}})
async def get_recipe(request: RecipeRequest):
    """
    주어진 음식 이름에 대한 레시피를 검색하거나 생성합니다.
    사용자의 선호도를 반영하고, 선택적으로 냉장고 재료만 사용하도록 설정할 수 있습니다.
    """
    try:
        # 데이터베이스에서 레시피 검색
        recipe_data = await recipe_collection.find_one({"name": request.food_name})

        if recipe_data:
            # 이미 존재하는 레시피 정보 반환
            image_base64 = recipe_data.pop('image_base64', None)
            recipe = Recipe(**recipe_data)
            return RecipeResponse(id=str(recipe_data['_id']), recipe=recipe, image_base64=image_base64)

        # 선호도 정보 가져오기
        preferences = await preference_collection.find().to_list(length=None)
        preference_info = ""
        if preferences:
            like_keywords = [p["name"] for p in preferences if p["type"] == "like"]
            dislike_keywords = [p["name"] for p in preferences if p["type"] == "dislike"]
            preference_info = f"""
            선호하는 재료/맛: {', '.join(like_keywords)}
            기피하는 재료/맛: {', '.join(dislike_keywords)}
            """

        # 냉장고 재료 정보 가져오기
        refrigerator_info = ""
        if request.use_refrigerator:
            ingredients = await refrigerator_collection.find().to_list(length=None)
            if ingredients:
                available_ingredients = [f"{i['name']} ({i['amount']}{i['unit']})" for i in ingredients]
                refrigerator_info = f"""
                사용 가능한 재료:
                {', '.join(available_ingredients)}
                
                위 재료들만 사용하여 레시피를 만들어주세요.
                """

        # 레시피 생성 프롬프트
        recipe_prompt = f"""'{request.food_name}'에 대한 상세한 레시피를 JSON 형식으로 생성해주세요.

        {preference_info}
        {refrigerator_info}

        다음 구조를 따라주세요:
        {{
          "name": "{request.food_name}",
          "description": "요리에 대한 간단한 설명 (역사, 특징, 맛 등)",
          "cookTime": "총 조리 시간 (예: '1시간 30분')",
          "nutrition": {{
            "calories": 1인분 기준 칼로리 (정수),
            "protein": "단백질(g)",
            "carbohydrates": "탄수화물(g)",
            "fat": "지방(g)"
          }},
          "ingredients": [
            {{
              "name": "재료 이름",
              "amount": 양 (숫자),
              "unit": "단위 (g, ml, 개 등)"
            }}
          ],
          "instructions": [
            {{
              "step": 단계 번호 (정수),
              "description": "상세한 조리 방법 설명"
            }}
          ]
        }}

        주의사항:
        1. 재료는 최소 5개 이상 포함해주세요.
        2. 조리 단계는 최소 5단계 이상으로 상세히 설명해주세요.
        3. 각 단계별 설명은 초보자도 이해할 수 있도록 구체적이고 명확하게 작성해주세요.
        4. 영양 정보는 1인분 기준으로 제공해주세요.
        5. 선호도 정보를 고려하여 레시피를 조정해주세요.
        6. 냉장고 재료 사용이 지정된 경우, 해당 재료들만 사용하여 레시피를 만들어주세요.
        7. 반드시 유효한 JSON 형식으로만 응답해주세요. 추가 설명이나 주석은 불필요합니다.
        """

        recipe_response = openai_client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 세계적인 요리 전문가입니다. 다양한 요리법과 식재료에 대한 깊은 이해를 바탕으로, 정확하고 맛있는 레시피를 제공합니다."},
                {"role": "user", "content": recipe_prompt}
            ]
        )

        # ChatGPT 응답 파싱
        response_content = recipe_response.choices[0].message.content.strip()

        # 코드 블록 제거 및 JSON 추출
        json_content = re.search(r'\{[\s\S]*\}', response_content)
        if json_content:
            response_content = json_content.group()

        recipe_json = json.loads(response_content)
        recipe = Recipe(**recipe_json)

        image_prompt = f"""Create a high-quality, photorealistic image of {recipe.name} with the following specifications:

        1. Subject: A beautifully plated dish of {recipe.name}, ready to be served.
        2. Setting: Place the dish in a context that complements its style and origin (e.g., rustic table for homestyle dishes, elegant setting for gourmet meals).
        3. Lighting: Use soft, warm lighting to enhance the appetizing appearance of the food.
        4. Composition: 
           - The main dish should be the focal point, occupying about 70% of the frame.
           - Include some garnishes or side elements that complement the main dish.
           - You may include some background elements to set the scene (e.g., table setting, complementary ingredients).
        5. Style: Professional food photography style, as if for a high-end restaurant menu or cookbook.
        6. Details to highlight:
           - Texture and color of the main ingredients
           - Any unique features mentioned in the recipe description
           - Garnishes or toppings that make the dish visually appealing

        Recipe details:
        - Description: {recipe.description}
        - Main ingredients: {', '.join([ingredient.name for ingredient in recipe.ingredients[:5]])}

        Additional notes:
        - Ensure the image looks appetizing and showcases the dish in its best light.
        - The plating should reflect the style and origin of the dish.
        - Avoid any text or labels in the image.
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

        recipe_dict = recipe.model_dump()
        recipe_dict['image_base64'] = image_base64  # URL 대신 Base64 인코딩된 이미지 저장
        result = await recipe_collection.insert_one(recipe_dict)
        recipe_id = str(result.inserted_id)

        return RecipeResponse(id=recipe_id, recipe=recipe, image_base64=image_base64)

    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
        raise HTTPException(status_code=400, detail=f"생성된 레시피 정보를 JSON으로 파싱할 수 없습니다: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
