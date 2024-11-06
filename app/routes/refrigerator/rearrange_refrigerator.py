import json
import logging
import re

from fastapi import APIRouter, HTTPException

from app.config import client as openai_client
from app.database import refrigerator_collection
from app.models.error_models import ErrorResponse
from app.models.refrigerator.refrigerator_models import GetIngredientsResponse, Refrigerator, IngredientCategory, \
    Ingredient

router = APIRouter()


@router.post("/refrigerator/rearrange-refrigerator", tags=["Refrigerator"], response_model=GetIngredientsResponse,
             responses={400: {"model": ErrorResponse}})
async def rearrange_refrigerator():
    try:
        # 현재 냉장고 내용물 가져오기
        ingredients = await refrigerator_collection.find().to_list(length=None)

        # ChatGPT에 보낼 메시지 준비
        rearrange_prompt = f"""현재 냉장고 내용물을 분석하고, 최적화된 재배치 방안을 JSON 형식으로 제공해주세요. 다음 구조를 따라주세요:

        {{
          "categories": [
            {{
              "category": "카테고리명",
              "ingredients": [
                {{
                  "name": "재료명",
                  "amount": 수량,
                  "unit": "단위"
                }}
              ],
            }}
          ],
        }}

        현재 냉장고 내용물:
        {json.dumps([{
            "name": ing["name"],
            "amount": ing["amount"],
            "unit": ing["unit"],
            "category": ing["category"]
        } for ing in ingredients], ensure_ascii=False)}

        주의사항:
        1. 기존 카테고리를 최대한 유지하되, 필요한 경우 새로운 카테고리를 만들거나 기존 카테고리를 병합하세요.
        2. 반드시 유효한 JSON 형식으로만 응답해주세요. 추가 설명이나 주석은 불필요합니다.
        """

        # ChatGPT로부터 제안 받기
        response = openai_client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "당신은 식품 보관 및 냉장고 정리 전문가입니다. 식재료의 특성을 고려하여 최적의 보관 방법과 냉장고 정리 방안을 제시합니다."},
                {"role": "user", "content": rearrange_prompt}
            ]
        )

        # ChatGPT 응답 파싱
        response_content = response.choices[0].message.content.strip()

        # 코드 블록 제거 및 JSON 추출
        json_content = re.search(r'\{[\s\S]*\}', response_content)
        if json_content:
            response_content = json_content.group()

        try:
            optimized_data = json.loads(response_content)
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            raise HTTPException(status_code=400, detail=f"생성된 정보를 JSON으로 파싱할 수 없습니다: {e}")

        if 'categories' not in optimized_data:
            raise HTTPException(status_code=500, detail="Invalid optimization suggestion format")

        # 현재 냉장고 내용물 비우기
        await refrigerator_collection.delete_many({})

        # 최적화된 재료를 데이터베이스에 다시 삽입
        for category in optimized_data['categories']:
            for ingredient in category['ingredients']:
                await refrigerator_collection.insert_one({
                    "name": ingredient['name'],
                    "amount": ingredient['amount'],
                    "unit": ingredient['unit'],
                    "category": category['category']
                })

        # 업데이트된 냉장고 내용물 가져오기
        updated_ingredients = await refrigerator_collection.find().to_list(length=None)

        # 응답 준비
        categories = []
        for category in optimized_data['categories']:
            category_ingredients = [
                Ingredient(id=str(ing['_id']), name=ing['name'], amount=ing['amount'], unit=ing['unit'],
                           category=ing['category'])
                for ing in updated_ingredients if ing['category'] == category['category']
            ]
            categories.append(IngredientCategory(
                category=category['category'],
                ingredients=category_ingredients,
            ))

        refrigerator = Refrigerator(
            categories=categories,
        )
        return GetIngredientsResponse(refrigerator=refrigerator)


    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
