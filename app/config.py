import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
MONGODB_URL = os.environ.get("MONGODB_URL")
