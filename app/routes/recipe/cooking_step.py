import json

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.config import client as openai_client
from app.database import recipe_collection, cooking_step_collection
from app.models.error_models import ErrorResponse
from app.models.recipe.cooking_step_models import CookingStepRequest, CookingStep, CookingStepResponse
from app.utils.image_utils import download_and_encode_image

router = APIRouter()


@router.post("/recipe/cooking_step", tags=["Recipe"], response_model=CookingStepResponse,
             responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def get_cooking_step_info(request: CookingStepRequest):
    """
    레시피의 특정 조리 단계에 대한 상세 정보를 반환하거나 생성합니다.
    """
    try:
        # 기존 조리 단계 정보 검색
        existing_step = await cooking_step_collection.find_one({
            "recipe_id": request.recipe_id,
            "step_number": request.step_number
        })

        if existing_step:
            # 기존 정보가 있으면 그대로 반환
            cooking_step = CookingStep(**existing_step)
            return CookingStepResponse(
                id=str(existing_step['_id']),
                cooking_step=cooking_step,
                image_base64=existing_step.get('image_base64')
            )

        # 기존 정보가 없으면 새로 생성
        recipe = await recipe_collection.find_one({"_id": ObjectId(request.recipe_id)})
        if not recipe:
            raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다.")

        # 레시피의 필요한 정보만 추출
        recipe_context = {
            "name": recipe['name'],
            "ingredients": recipe['ingredients'],
            "instructions": recipe['instructions'][request.step_number - 1] if request.step_number <= len(
                recipe['instructions']) else None
        }

        cooking_step_prompt = f"""제공된 레시피에 대한 자세한 조리 과정 정보를 JSON 형식으로 생성해주세요. 다음 구조를 따라주세요:

        {{
          "recipe_id": "레시피 ID",
          "step_number": 단계 번호,
          "description": "조리 과정에 대한 상세한 설명과 팁",
        }}

        레시피 ID: {request.recipe_id}
        단계 번호: {request.step_number}
        레시피 정보: {json.dumps(recipe_context, ensure_ascii=False)}
        
        주의: 반드시 다른 텍스트나 코드블록 없이 유효한 JSON 형식으로만 응답해주세요.
        """

        cooking_step_response = openai_client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 전문 요리사입니다. 주어진 레시피의 특정 조리 단계에 대한 상세한 정보를 JSON 형식으로 제공합니다."},
                {"role": "user", "content": cooking_step_prompt}
            ]
        )

        cooking_step_json = json.loads(cooking_step_response.choices[0].message.content)
        cooking_step = CookingStep(**cooking_step_json)

        image_prompt = f"""A high-quality, detailed photo demonstrating the cooking step for {recipe_context['name']}, step number {cooking_step.step_number}:

        - Description: {cooking_step.description}

        The image should clearly show the action being performed.
        Ensure the lighting is bright and even, showcasing the details of the cooking process.
        The image should be from a slightly elevated angle to give a clear view of the cooking surface and the chef's hands (if applicable).
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

        cooking_step_dict = cooking_step.model_dump()
        cooking_step_dict['image_base64'] = image_base64  # URL 대신 Base64 인코딩된 이미지 저장
        result = await cooking_step_collection.insert_one(cooking_step_dict)
        cooking_step_id = str(result.inserted_id)

        return CookingStepResponse(id=cooking_step_id, cooking_step=cooking_step, image_base64=image_base64)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="생성된 조리 과정 정보를 JSON으로 파싱할 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
