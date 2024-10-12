import base64
import json
import logging
import re

from fastapi import APIRouter, File, UploadFile, HTTPException

from app.config import client
from app.models.error_models import ErrorResponse
from app.models.refrigerator.ingredient_detect_models import IngredientDetectResponse, NoIngredientsFoundResponse

router = APIRouter()


@router.post("/refrigerator/ingredient-detect", tags=["Refrigerator"],
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
        ingredient_detect_prompt = f"""제공된 이미지에서 식재료를 상세히 분석하고 인식해주세요. 다음 지침을 따라 JSON 형식으로 응답해주세요:

        1. 모든 식별 가능한 식재료를 나열하세요.
        2. 가공식품, 조리된 음식, 음료 등도 포함하여 모든 식품을 식재료로 간주하세요.
        3. 식재료의 상태나 형태가 특이한 경우(예: 썬 당근, 으깬 감자 등)에도 기본 식재료 이름으로 나열하세요.
        4. 동일한 식재료가 여러 번 나타나더라도 한 번만 나열하세요.
        5. 식재료 이름은 가능한 한 일반적이고 기본적인 형태로 제시하세요(예: '로메인 상추' 대신 '상추').

        다음 JSON 구조를 따라 응답해주세요:

        {{
          "ingredients": [
            "식재료1",
            "식재료2",
            "식재료3"
          ]
        }}

        만약 이미지에서 식재료를 찾을 수 없다면, 다음과 같이 빈 리스트를 반환해주세요:
        {{
          "ingredients": []
        }}
        
        주의: 
        1. 반드시 다른 텍스트나 코드블록 없이 유효한 JSON 형식으로만 응답해주세요.
        2. 식재료나 음식이 확실하지 않은 경우, 가장 가능성 있는 추측을 제공하세요.
        3. 이미지에 식재료나 음식과 관련 없는 물체가 있더라도 무시하고 식재료와 음식에만 집중해주세요.
        """

        # OpenAI API 호출
        ingredient_detect_response = client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 요리와 식재료 전문가입니다. 제공된 이미지에서 모든 식재료와 식품을 정확하게 식별하고 분석할 수 있습니다."},
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
        )

        # ChatGPT 응답 파싱
        response_content = ingredient_detect_response.choices[0].message.content.strip()

        # 코드 블록 제거 및 JSON 추출
        json_content = re.search(r'\{[\s\S]*\}', response_content)
        if json_content:
            response_content = json_content.group()

        try:
            ingredient_detect_json = json.loads(response_content)
            detected_ingredients = ingredient_detect_json.get("ingredients", [])
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            raise HTTPException(status_code=400, detail=f"생성된 식재료 정보를 JSON으로 파싱할 수 없습니다: {e}")

        if not detected_ingredients:
            return NoIngredientsFoundResponse()

        return IngredientDetectResponse(ingredients=detected_ingredients)

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
