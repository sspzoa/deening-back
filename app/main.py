from fastapi import FastAPI
from app.routes import ping, recipe, ingredient, cooking_step

app = FastAPI(
    title="Deening API",
    description="Best Recipe Service powered by AI.",
    version="0.1.0"
)

app.include_router(ping.router)
app.include_router(recipe.router)
app.include_router(ingredient.router)
app.include_router(cooking_step.router)
