from fastapi import APIRouter, HTTPException
from app.models.cooking_step_models import CookingStepRequest, CookingStep, CookingStepResponse
from pydantic import BaseModel
from app.config import client
import json

from app.routes.recipe import recipe_store

router = APIRouter()

class ErrorResponse(BaseModel):
    error: str

@router.post("/cooking_step", response_model=CookingStepResponse, responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def get_cooking_step_info(request: CookingStepRequest):
    """
    레시피의 특정 조리 단계에 대한 상세 정보를 생성합니다.
    """
    if request.recipe_id not in recipe_store:
        raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다.")

    stored_data = recipe_store[request.recipe_id]
    recipe = stored_data["recipe"]

    try:
        # 조리 과정 정보 생성 프롬프트
        cooking_step_prompt = f"""제공된 레시피에 대한 자세한 조리 과정 정보를 JSON 형식으로 생성해주세요. 다음 구조를 따라주세요:

        {{
          "recipe_id": "레시피 ID",
          "step_number": 단계 번호,
          "description": "조리 과정에 대한 상세한 설명",
          "duration": "예상 소요 시간",
          "tools_needed": ["도구1", "도구2", "도구3"],
          "ingredients_used": ["재료1", "재료2", "재료3"],
          "tips": "이 단계를 위한 요리 팁"
        }}

        레시피 ID: {request.recipe_id}
        단계 번호: {request.step_number}
        레시피: {recipe}
        """

        # 조리 과정 정보 생성
        cooking_step_response = client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 전문 요리사입니다. 주어진 레시피의 특정 조리 단계에 대한 상세한 정보를 JSON 형식으로 제공합니다."},
                {"role": "user", "content": cooking_step_prompt}
            ]
        )

        cooking_step_json = json.loads(cooking_step_response.choices[0].message.content)
        cooking_step = CookingStep(**cooking_step_json)

        # 이미지 생성 프롬프트
        image_prompt = f"""A high-quality, detailed photo demonstrating the cooking step for {recipe.name}, step number {cooking_step.step_number}:

        - Description: {cooking_step.description}
        - Tools used: {', '.join(cooking_step.tools_needed)}
        - Ingredients involved: {', '.join(cooking_step.ingredients_used)}

        The image should clearly show the action being performed, with visible ingredients and tools. 
        Ensure the lighting is bright and even, showcasing the details of the cooking process.
        The image should be from a slightly elevated angle to give a clear view of the cooking surface and the chef's hands (if applicable).
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

        return CookingStepResponse(cooking_step=cooking_step, image_url=image_url)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="생성된 조리 과정 정보를 JSON으로 파싱할 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))