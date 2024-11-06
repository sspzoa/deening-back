from pydantic import BaseModel


class ChatRequest(BaseModel):
    recipe_id: str
    question: str


class ChatResponse(BaseModel):
    answer: str
