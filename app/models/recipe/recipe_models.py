from typing import List

from pydantic import BaseModel


class Ingredient(BaseModel):
    name: str
    amount: float
    unit: str


class Instruction(BaseModel):
    step: int
    description: str


class Nutrition(BaseModel):
    calories: int
    protein: str
    carbohydrates: str
    fat: str


class Recipe(BaseModel):
    name: str
    description: str
    cookTime: str
    nutrition: Nutrition
    ingredients: List[Ingredient]
    instructions: List[Instruction]


class RecipeRequest(BaseModel):
    food_name: str


class RecipeResponse(BaseModel):
    id: str
    recipe: Recipe
    image_base64: str
