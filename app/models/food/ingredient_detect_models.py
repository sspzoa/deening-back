from typing import List

from fastapi import UploadFile
from pydantic import BaseModel


class IngredientDetectRequest(BaseModel):
    image: UploadFile


class IngredientDetectResponse(BaseModel):
    ingredients: List[str]


class NoIngredientsFoundResponse(BaseModel):
    message: str = "No ingredients found in the image"
