from pydantic import BaseModel
from typing import List

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
    servings: int
    prepTime: str
    cookTime: str
    totalTime: str
    difficulty: str
    ingredients: List[Ingredient]
    instructions: List[Instruction]
    nutrition: Nutrition
    tags: List[str]
    source: str

class RecipeRequest(BaseModel):
    food_name: str

class RecipeResponse(BaseModel):
    id: str
    recipe: Recipe
    image_url: str