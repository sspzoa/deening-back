from fastapi import FastAPI
from app.routes import ping, recipe, ingredient, cooking_step

app = FastAPI(
    title="Deening API",
    description="Best Recipe Service powered by AI.",
    version="0.1.0",
    contact={
        "name": "Seungpyo Suh",
        "url": "https://sspzoa.io/",
        "email": "me@sspzoa.io",
    },
    license_info={
        "name": "GNU Affero General Public License v3.0",
        "url": "https://www.gnu.org/licenses/agpl-3.0.en.html",
    },
)

app.include_router(ping.router)
app.include_router(recipe.router)
app.include_router(ingredient.router)
app.include_router(cooking_step.router)
