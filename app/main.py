import os
from pathlib import Path

from fastapi import FastAPI
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

@app.get("/ping")
async def ping():
    return {"message": "pong"}