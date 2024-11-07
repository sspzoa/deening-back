from typing import List

from pydantic import BaseModel


class SearchRequest(BaseModel):
    search_query: str


class RecipeSimple(BaseModel):
    id: str
    name: str
    image_url: str


class SearchResponse(BaseModel):
    search_results: List[RecipeSimple]
