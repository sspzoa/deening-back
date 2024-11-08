from typing import List, Literal

from pydantic import BaseModel

StorageType = Literal["REFRIGERATED", "FROZEN", "ROOM_TEMP"]


class Ingredient(BaseModel):
    id: str
    name: str
    amount: float
    unit: str
    category: str
    storage_type: StorageType


class AddIngredientForm(BaseModel):
    name: str
    amount: float
    unit: str
    category: str
    storage_type: StorageType


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
    name: str | None = None
    amount: float | None = None
    unit: str | None = None
    category: str | None = None
    storage_type: StorageType | None = None


class UpdateIngredientResponse(BaseModel):
    message: str
