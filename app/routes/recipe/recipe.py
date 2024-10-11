import json

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.config import client as openai_client
from app.database import recipe_collection
from app.models.error_models import ErrorResponse
from app.models.recipe.recipe_models import Recipe, RecipeRequest, RecipeResponse
from app.utils.image_utils import download_and_encode_image

router = APIRouter()

@router.post("/recipe", tags=["Recipe"], response_model=RecipeResponse, responses={400: {"model": ErrorResponse}})
async def get_or_create_recipe(request: RecipeRequest):
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
        recipe_prompt = f"""제공된 음식 이름에 대한 레시피를 JSON 형식으로 생성해주세요. 다음 구조를 따라주세요:

        {{
          "name": "레시피 이름",
          "description": "레시피에 대한 간단한 설명",
          "cookTime": "조리 시간",
          "nutrition": {{
            "calories": 칼로리(정수),
            "protein": "단백질(g)",
            "carbohydrates": "탄수화물(g)",
            "fat": "지방(g)"
          }},
          "ingredients": [
            {{
              "name": "재료 이름",
              "amount": 양(숫자),
              "unit": "단위"
            }}
          ],
          "instructions": [
            {{
              "step": 단계 번호(정수),
              "description": "단계 설명"
            }}
          ],
        }}

        음식 이름: {request.food_name}
        
        주의: 반드시 다른 텍스트나 코드블록 없이 유효한 JSON 형식으로만 응답해주세요.
        """

        recipe_response = openai_client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 요리 전문가입니다. 주어진 음식에 대한 상세한 레시피를 JSON 형식으로 제공합니다."},
                {"role": "user", "content": recipe_prompt}
            ]
        )

        print("OpenAI API Response:", recipe_response.choices[0].message.content)

        recipe_json = json.loads(recipe_response.choices[0].message.content)
        recipe = Recipe(**recipe_json)

        image_prompt = f"""A high-quality, appetizing photo of {recipe.name}, as described in the recipe. 
        The dish should look professionally plated and photographed, with attention to detail and presentation.

        Recipe details:
        - Description: {recipe.description}
        - Main ingredients: {', '.join([ingredient.name for ingredient in recipe.ingredients[:5]])}
        - Cuisine tags: {', '.join(recipe.tags)}

        The image should clearly show the main ingredients and reflect the cuisine style indicated by the tags. 
        Ensure the presentation matches the difficulty level of '{recipe.difficulty}' and serves {recipe.servings}.
        """

        image_response = openai_client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = image_response.data[0].url
        image_base64 = 'data:image/png;base64,' +  download_and_encode_image(image_url)  # 이미지 다운로드 및 Base64 인코딩

        recipe_dict = recipe.model_dump()
        recipe_dict['image_base64'] = image_base64  # URL 대신 Base64 인코딩된 이미지 저장
        result = await recipe_collection.insert_one(recipe_dict)
        recipe_id = str(result.inserted_id)

        return RecipeResponse(id=recipe_id, recipe=recipe, image_base64=image_base64)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="생성된 레시피를 JSON으로 파싱할 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/recipe/{recipe_id}", tags=["Recipe"], response_model=RecipeResponse,
            responses={404: {"model": ErrorResponse}})
async def get_recipe_by_id(recipe_id: str):
    """
    주어진 ID에 대한 레시피를 반환합니다.
    """
    try:
        recipe_data = await recipe_collection.find_one({"_id": ObjectId(recipe_id)})
        if not recipe_data:
            raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다.")

        image_base64 = recipe_data.pop('image_base64', None)
        recipe = Recipe(**recipe_data)
        return RecipeResponse(id=str(recipe_data['_id']), recipe=recipe, image_base64=image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))