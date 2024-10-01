from fastapi import FastAPI
from app.routes import ping, recipe

app = FastAPI(
    title="Deening API",
    description="Best Recipe Service powered by AI.",
    version="0.1.0"
)

app.include_router(ping.router)
app.include_router(recipe.router)
