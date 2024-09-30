import os

from fastapi import FastAPI
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

app = FastAPI(
    title="Deening API",
    description="Best Recipe Service powered by AI.",
    version="0.1.0"
)

@app.get("/ping")
async def root():
    return {"message": "pong"}