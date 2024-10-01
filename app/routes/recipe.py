from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.config import client
import json

router = APIRouter()

class RecipeRequest(BaseModel):
    food_name: str

class Ingredient(BaseModel):
    name: str
    amount: float
    unit: str

class Instruction(BaseModel):
    step: int
    description: str

class Nutrition(BaseModel):
    calories: int
    protein: str
    carbohydrates: str
    fat: str

class Recipe(BaseModel):
    name: str
    description: str
    servings: int
    prepTime: str
    cookTime: str
    totalTime: str
    difficulty: str
    ingredients: List[Ingredient]
    instructions: List[Instruction]
    nutrition: Nutrition
    tags: List[str]
    source: str

class RecipeResponse(BaseModel):
    recipe: Recipe
    image_url: str

class ErrorResponse(BaseModel):
    error: str

@router.post("/recipe", response_model=RecipeResponse, responses={400: {"model": ErrorResponse}})
async def get_recipe(request: RecipeRequest):
    try:
        # 레시피 생성 프롬프트
        recipe_prompt = f"""제공된 음식 이름에 대한 레시피를 JSON 형식으로 생성해주세요. 다음 구조를 따라주세요:

{{
  "name": "레시피 이름",
  "description": "레시피에 대한 간단한 설명",
  "servings": 인분 수(정수),
  "prepTime": "준비 시간",
  "cookTime": "조리 시간",
  "totalTime": "총 소요 시간",
  "difficulty": "난이도",
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
  "nutrition": {{
    "calories": 칼로리(정수),
    "protein": "단백질(g)",
    "carbohydrates": "탄수화물(g)",
    "fat": "지방(g)"
  }},
  "tags": ["태그1", "태그2", "태그3"],
  "source": "출처 또는 원작자"
}}

음식 이름: {request.food_name}
"""

        # 레시피 생성
        recipe_response = client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 요리 전문가입니다. 주어진 음식에 대한 상세한 레시피를 JSON 형식으로 제공합니다."},
                {"role": "user", "content": recipe_prompt}
            ]
        )

        recipe_json = json.loads(recipe_response.choices[0].message.content)
        recipe = Recipe(**recipe_json)

        # 이미지 생성 프롬프트
        image_prompt = f"""A high-quality, appetizing photo of {recipe.name}, as described in the recipe. 
The dish should look professionally plated and photographed, with attention to detail and presentation.

Recipe details:
- Description: {recipe.description}
- Main ingredients: {', '.join([ingredient.name for ingredient in recipe.ingredients[:5]])}
- Cuisine tags: {', '.join(recipe.tags)}

The image should clearly show the main ingredients and reflect the cuisine style indicated by the tags. 
Ensure the presentation matches the difficulty level of '{recipe.difficulty}' and serves {recipe.servings}.
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

        return RecipeResponse(recipe=recipe, image_url=image_url)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="생성된 레시피를 JSON으로 파싱할 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))