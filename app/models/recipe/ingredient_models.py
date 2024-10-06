from typing import List

from pydantic import BaseModel


class IngredientRequest(BaseModel):
    ingredient_name: str


class NutritionalInfo(BaseModel):
    calories: int
    protein: float
    carbohydrates: float
    fat: float
    fiber: float
    vitamins: str
    minerals: str


class Ingredient(BaseModel):
    name: str
    description: str
    category: str
    nutritional_info: NutritionalInfo
    storage_tips: str
    culinary_uses: List[str]


class IngredientResponse(BaseModel):
    id: str
    ingredient: Ingredient
    image_base64: str
