import base64
import json
import logging

from fastapi import APIRouter, File, UploadFile, HTTPException

from app.config import client
from app.models.error_models import ErrorResponse
from app.models.food.ingredient_detect_models import IngredientDetectResponse, NoIngredientsFoundResponse

router = APIRouter()

@router.post("/ingredient_detect", tags=["Food"],
             response_model=IngredientDetectResponse,
             responses={400: {"model": ErrorResponse}, 404: {"model": NoIngredientsFoundResponse}})
async def ingredient_detect(image: UploadFile = File(...)):
    """
    업로드된 이미지 파일에서 식재료를 탐색해 반환합니다.
    """

    try:
        # 이미지 파일 읽기
        contents = await image.read()

        # Base64로 인코딩
        b64_image = base64.b64encode(contents).decode('utf-8')

        # 식재료 탐색 프롬프트
        ingredient_detect_prompt = f"""제공된 이미지에서 식재료를 탐색하고 인식해주세요. 다음 JSON 구조를 따라 응답해주세요:

        {{
          "ingredients": [
            "식재료1",
            "식재료2",
            "식재료3"
          ]
        }}

        만약 이미지에서 식재료를 찾을 수 없다면, 빈 리스트를 반환해주세요:
        {{
          "ingredients": []
        }}

        주의: 반드시 다른 텍스트 없이 유효한 JSON 형식으로만 응답해주세요.
        """

        # OpenAI API 호출
        ingredient_detect_response = client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 요리 전문가입니다. 제공된 이미지에서 식재료를 탐색하고 인식합니다."},
                {"role": "user", "content": [
                    {"type": "text", "text": ingredient_detect_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}",
                        },
                    },
                ],
                 }
            ],
            max_tokens=300,
        )

        try:
            ingredient_detect_json = json.loads(ingredient_detect_response.choices[0].message.content)
            detected_ingredients = ingredient_detect_json.get("ingredients", [])
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="생성된 식재료 정보를 JSON으로 파싱할 수 없습니다.")

        if not detected_ingredients:
            return NoIngredientsFoundResponse()

        return IngredientDetectResponse(ingredients=detected_ingredients)

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")