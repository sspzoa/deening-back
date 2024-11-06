from enum import Enum
from typing import List

from pydantic import BaseModel


class KeywordType(str, Enum):
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"


class Keyword(BaseModel):
    id: str
    name: str
    type: KeywordType


class AddKeywordRequest(BaseModel):
    name: str
    type: KeywordType


class AddKeywordResponse(BaseModel):
    message: str


class DeleteKeywordResponse(BaseModel):
    message: str


class Preference(BaseModel):
    keywords: List[Keyword]


class GetKeywordsResponse(BaseModel):
    preference: Preference


class UpdateKeywordRequest(BaseModel):
    name: str | None = None
    type: KeywordType | None = None


class UpdateKeywordResponse(BaseModel):
    message: str
