from pydantic import BaseModel
from typing import List
from fastapi import UploadFile

class IngredientDetectRequest(BaseModel):
    image: UploadFile

class DetectedIngredient(BaseModel):
    ingredient_name: str

class IngredientDetectResponse(BaseModel):
    ingredients: List[DetectedIngredient]

class NoIngredientsFoundResponse(BaseModel):
    message: str = "No ingredients found in the image"