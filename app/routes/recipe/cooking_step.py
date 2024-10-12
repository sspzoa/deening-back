import json
import logging
import re

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.config import client as openai_client
from app.database import recipe_collection, cooking_step_collection
from app.models.error_models import ErrorResponse
from app.models.recipe.cooking_step_models import CookingStepRequest, CookingStep, CookingStepResponse
from app.utils.image_utils import download_and_encode_image

router = APIRouter()
logging.basicConfig(level=logging.DEBUG)


@router.post("/recipe/cooking-step", tags=["Recipe"], response_model=CookingStepResponse,
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

        # Format ingredients based on their structure
        if isinstance(recipe_context['ingredients'][0], dict):
            formatted_ingredients = ', '.join(
                [f"{ing.get('name', 'Unknown')} ({ing.get('amount', 'Unknown amount')})" for ing in
                 recipe_context['ingredients']])
        else:
            formatted_ingredients = ', '.join(recipe_context['ingredients'])

        cooking_step_prompt = f"""레시피 '{recipe_context['name']}'의 {request.step_number}번째 조리 단계에 대한 상세 정보를 JSON 형식으로 제공해주세요.

        레시피 컨텍스트:
        - 재료: {formatted_ingredients}
        - 현재 단계 지침: {recipe_context['instructions']}

        다음 구조를 따라 자세한 정보를 작성해주세요:
        {{
          "recipe_id": "{request.recipe_id}",
          "step_number": {request.step_number},
          "description": "조리 과정에 대한 상세한 설명. 다음 내용을 포함해주세요:
            1. 정확한 조리 방법과 기술
            2. 주의해야 할 점
            3. 시간이나 온도와 같은 구체적인 수치
            4. 재료의 상태나 질감에 대한 설명
            5. 이 단계를 잘 수행하기 위한 팁이나 요령"
        }}

        주의사항:
        1. 설명은 초보자도 이해하기 쉽게 상세하고 명확하게 작성해주세요.
        2. 안전과 관련된 주의사항이 있다면 반드시 포함시켜주세요.
        3. 요리의 맛과 품질을 향상시킬 수 있는 전문적인 조언을 제공해주세요.
        4. 반드시 유효한 JSON 형식으로만 응답해주세요. 추가 설명이나 주석은 불필요합니다.
        """

        logging.debug(f"Cooking step prompt: {cooking_step_prompt}")

        cooking_step_response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system",
                 "content": "당신은 세계적인 요리 전문가입니다. 다양한 요리 기법과 재료에 대한 깊은 이해를 바탕으로, 정확하고 유용한 조리 정보를 제공합니다."},
                {"role": "user", "content": cooking_step_prompt}
            ]
        )

        # Log the full response for debugging
        logging.debug(f"OpenAI API response: {cooking_step_response}")

        # ChatGPT 응답 파싱
        response_content = cooking_step_response.choices[0].message.content.strip()
        logging.debug(f"Stripped response content: {response_content}")

        # 코드 블록 제거 및 JSON 추출
        json_content = re.search(r'\{[\s\S]*\}', response_content)
        if json_content:
            response_content = json_content.group()
            logging.debug(f"Extracted JSON content: {response_content}")
        else:
            logging.error("No JSON content found in the response")
            raise ValueError("No JSON content found in the response")

        try:
            cooking_step_json = json.loads(response_content)
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            raise ValueError(f"Invalid JSON: {e}")

        logging.debug(f"Parsed JSON: {cooking_step_json}")

        cooking_step = CookingStep(**cooking_step_json)

        image_prompt = f"""Create a photorealistic image for the following cooking step:

        Recipe: {recipe_context['name']}
        Step Number: {cooking_step.step_number}
        Description: {cooking_step.description}

        Image requirements:
        1. Show a close-up, detailed view of the exact action being performed.
        2. Include the chef's hands and relevant utensils or equipment.
        3. Ensure the ingredients or dish are clearly visible and identifiable.
        4. Use bright, even lighting to highlight all details of the cooking process.
        5. Capture the image from a slightly elevated angle (about 30-45 degrees) to provide a clear view of the cooking surface and action.
        6. Reflect the correct stage of cooking (e.g., raw ingredients, partially cooked, or finished dish).
        7. Include any specific visual cues mentioned in the step description (e.g., color changes, texture, or consistency).

        Style: Photorealistic, high-quality food photography suitable for a professional cookbook or culinary website.
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

    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
        raise HTTPException(status_code=400, detail=f"생성된 조리 과정 정보를 JSON으로 파싱할 수 없습니다: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
