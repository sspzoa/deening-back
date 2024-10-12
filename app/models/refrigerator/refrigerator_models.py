from typing import List

from pydantic import BaseModel


class Ingredient(BaseModel):
    id: str
    name: str
    amount: float
    unit: str
    category: str


class AddIngredientForm(BaseModel):
    name: str
    amount: float
    unit: str
    category: str


class AddIngredientRequest(BaseModel):
    ingredients: List[AddIngredientForm]


class AddIngredientResponse(BaseModel):
    message: str


class DeleteIngredientResponse(BaseModel):
    message: str


class IngredientCategory(BaseModel):
    category: str
    ingredients: List[Ingredient]


class Refrigerator(BaseModel):
    categories: List[IngredientCategory]


class GetIngredientsResponse(BaseModel):
    refrigerator: Refrigerator


class GetIngredientsByCategoryResponse(BaseModel):
    category: str
    ingredients: List[Ingredient]


class UpdateIngredientRequest(BaseModel):
    name: str
    amount: float
    unit: str
    category: str


class UpdateIngredientResponse(BaseModel):
    message: str
