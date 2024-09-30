import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

app = FastAPI(
    title="Deening API",
    description="Best Recipe Service powered by AI.",
    version="0.1.0"
)

class Prompt(BaseModel):
    prompt: str

class PingResponse(BaseModel):
    message: str

class GeneratedResponse(BaseModel):
    generated_text: str

class ErrorResponse(BaseModel):
    error: str

@app.get("/ping", response_model=PingResponse)
async def ping():
    return {"message": "pong"}

@app.post("/generate", response_model=GeneratedResponse, responses={400: {"model": ErrorResponse}})
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