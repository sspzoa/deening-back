import logging

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.config import client as openai_client
from app.database import recipe_collection
from app.models.error_models import ErrorResponse
from app.models.recipe.chat_models import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/recipe/chat", tags=["Recipe"], response_model=ChatResponse,
             responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def chat_with_recipe(request: ChatRequest):
    """
    레시피에 대한 질문을 처리하고 답변을 제공합니다.
    """
    try:
        # 레시피 데이터 조회
        recipe = await recipe_collection.find_one({"_id": ObjectId(request.recipe_id)})
        if not recipe:
            raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다.")

        # 영양 정보 문자열 구성
        nutrition_info = (f"칼로리: {recipe['nutrition']['calories']}kcal, "
                          f"단백질: {recipe['nutrition']['protein']}g, "
                          f"탄수화물: {recipe['nutrition']['carbohydrates']}g, "
                          f"지방: {recipe['nutrition']['fat']}g")

        # 재료 목록 문자열 구성
        ingredients_list = "\n".join(
            f"- {ing['name']}: {ing['amount']}{ing['unit']}"
            for ing in recipe['ingredients']
        )

        # 조리 과정 문자열 구성
        instructions_list = "\n".join(
            f"{step['step']}. {step['description']}"
            for step in recipe['instructions']
        )

        # 챗봇 프롬프트 구성
        chat_prompt = f"""다음은 '{recipe['name']}'에 대한 레시피 정보입니다:

        요리 설명: {recipe['description']}
        조리 시간: {recipe['cookTime']}
        영양 정보: {nutrition_info}
        
        재료:
        {ingredients_list}
        
        조리 과정:
        {instructions_list}

        사용자의 질문: {request.question}

        주의사항:
        1. 답변은 친절하고 이해하기 쉽게, 간결하게 작성해주세요.
        2. 줄바꿈이나 마크다운 문법 없이 채팅 형식으로 작성해주세요.
        """

        # ChatGPT API 호출
        chat_response = openai_client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 요리 전문가입니다. 레시피와 조리 방법에 대한 질문에 친절하고 전문적으로 답변해주세요."},
                {"role": "user", "content": chat_prompt}
            ]
        )

        # 응답 처리
        answer = chat_response.choices[0].message.content.strip()

        return ChatResponse(answer=answer)

    except Exception as e:
        logging.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
