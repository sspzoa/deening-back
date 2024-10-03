from typing import List

from pydantic import BaseModel


class CookingStepRequest(BaseModel):
    recipe_id: str
    step_number: int


class CookingStep(BaseModel):
    recipe_id: str
    step_number: int
    description: str
    duration: str
    tools_needed: List[str]
    ingredients_used: List[str]
    tips: str


class CookingStepResponse(BaseModel):
    id: str
    cooking_step: CookingStep
    image_url: str
