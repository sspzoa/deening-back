import json

from fastapi import APIRouter, HTTPException

from app.config import client as openai_client
from app.database import recipe_collection
from app.models.error_models import ErrorResponse
from app.models.recipe.recipe_models import Recipe, RecipeRequest, RecipeResponse
from app.utils.image_utils import download_and_encode_image

router = APIRouter()


@router.post("/recipe", tags=["Recipe"], response_model=RecipeResponse, responses={400: {"model": ErrorResponse}})
async def get_recipe(request: RecipeRequest):
    """
    주어진 음식 이름에 대한 레시피를 검색하거나 생성합니다.
    """
    try:
        # 데이터베이스에서 레시피 검색
        recipe_data = await recipe_collection.find_one({"name": request.food_name})

        if recipe_data:
            # 이미 존재하는 레시피 정보 반환
            image_base64 = recipe_data.pop('image_base64', None)
            recipe = Recipe(**recipe_data)
            return RecipeResponse(id=str(recipe_data['_id']), recipe=recipe, image_base64=image_base64)

        # 레시피가 없으면 새로 생성
        recipe_prompt = f"""'{request.food_name}'에 대한 상세한 레시피를 JSON 형식으로 생성해주세요. 다음 구조를 따라주세요:

        {{
          "name": "{request.food_name}",
          "description": "요리에 대한 간단한 설명 (역사, 특징, 맛 등)",
          "cookTime": "총 조리 시간 (예: '1시간 30분')",
          "difficulty": "난이도 (쉬움, 보통, 어려움 중 하나)",
          "servings": 몇 인분인지 (정수),
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
          ],
          "tips": [
            "요리 팁이나 중요 포인트 (2-3개)"
          ],
          "utensils": [
            "필요한 조리 도구 목록"
          ]
        }}

        주의사항:
        1. 재료는 최소 5개 이상 포함해주세요.
        2. 조리 단계는 최소 5단계 이상으로 상세히 설명해주세요.
        3. 각 단계별 설명은 초보자도 이해할 수 있도록 구체적이고 명확하게 작성해주세요.
        4. 영양 정보는 1인분 기준으로 제공해주세요.
        5. 요리 팁은 맛이나 질감을 향상시키는 실용적인 조언을 포함해주세요.
        6. 반드시 유효한 JSON 형식으로만 응답해주세요. 추가 설명이나 주석은 불필요합니다.
        """

        recipe_response = openai_client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 세계적인 요리 전문가입니다. 다양한 요리법과 식재료에 대한 깊은 이해를 바탕으로, 정확하고 맛있는 레시피를 제공합니다."},
                {"role": "user", "content": recipe_prompt}
            ]
        )

        recipe_json = json.loads(recipe_response.choices[0].message.content)
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
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="생성된 레시피를 JSON으로 파싱할 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
