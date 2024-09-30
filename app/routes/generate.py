from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import client

router = APIRouter()

class Prompt(BaseModel):
    prompt: str

class GeneratedResponse(BaseModel):
    generated_text: str

class ErrorResponse(BaseModel):
    error: str

@router.post("/generate", response_model=GeneratedResponse, responses={400: {"model": ErrorResponse}})
async def generate(prompt: Prompt):
    try:
        response = client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt.prompt}
            ]
        )
        return {"generated_text": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))