from pydantic import BaseModel


class ReplaceIngredientRequest(BaseModel):
    recipe_id: str
    ingredient_name: str


class ReplaceIngredientResponse(BaseModel):
    replaced_ingredient: str
    taste_change_description: str
