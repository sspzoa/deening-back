import json

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import client as openai_client
from app.database import recipe_collection, cooking_step_collection
from app.models.recipe.cooking_step_models import CookingStepRequest, CookingStep, CookingStepResponse

router = APIRouter()


class ErrorResponse(BaseModel):
    error: str


@router.post("/cooking_step", tags=["Recipe"], response_model=CookingStepResponse,
             responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def get_or_create_cooking_step_info(request: CookingStepRequest):
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
                image_url=existing_step.get('image_url')
            )

        # 기존 정보가 없으면 새로 생성
        recipe = await recipe_collection.find_one({"_id": ObjectId(request.recipe_id)})
        if not recipe:
            raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다.")

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
        
        주의: 반드시 다른 텍스트 없이 유효한 JSON 형식으로만 응답해주세요.
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

        image_prompt = f"""A high-quality, detailed photo demonstrating the cooking step for {recipe['name']}, step number {cooking_step.step_number}:

        - Description: {cooking_step.description}
        - Tools used: {', '.join(cooking_step.tools_needed)}
        - Ingredients involved: {', '.join(cooking_step.ingredients_used)}

        The image should clearly show the action being performed, with visible ingredients and tools. 
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

        cooking_step_dict = cooking_step.dict()
        cooking_step_dict['image_url'] = image_url
        result = await cooking_step_collection.insert_one(cooking_step_dict)
        cooking_step_id = str(result.inserted_id)

        print(cooking_step_response)
        print(image_response)

        return CookingStepResponse(id=cooking_step_id, cooking_step=cooking_step, image_url=image_url)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="생성된 조리 과정 정보를 JSON으로 파싱할 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cooking_step/{cooking_step_id}", tags=["Recipe"], response_model=CookingStepResponse,
            responses={404: {"model": ErrorResponse}})
async def get_cooking_step_by_id(cooking_step_id: str):
    """
    주어진 ID에 대한 조리 단계 정보를 반환합니다.
    """
    try:
        cooking_step_data = await cooking_step_collection.find_one({"_id": ObjectId(cooking_step_id)})
        if not cooking_step_data:
            raise HTTPException(status_code=404, detail="조리 단계 정보를 찾을 수 없습니다.")

        image_url = cooking_step_data.pop('image_url', None)
        cooking_step = CookingStep(**cooking_step_data)
        return CookingStepResponse(id=str(cooking_step_data['_id']), cooking_step=cooking_step, image_url=image_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
