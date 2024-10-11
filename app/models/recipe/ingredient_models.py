from typing import List

from pydantic import BaseModel


class IngredientRequest(BaseModel):
    ingredient_name: str


class Ingredient(BaseModel):
    name: str
    description: str


class IngredientResponse(BaseModel):
    id: str
    ingredient: Ingredient
    image_base64: str
