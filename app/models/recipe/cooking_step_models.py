from pydantic import BaseModel


class CookingStepRequest(BaseModel):
    recipe_id: str
    step_number: int


class CookingStep(BaseModel):
    recipe_id: str
    step_number: int
    description: str


class CookingStepResponse(BaseModel):
    id: str
    cooking_step: CookingStep
    image_base64: str
