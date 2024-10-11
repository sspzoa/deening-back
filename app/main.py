from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles

from app.dependencies.auth import verify_token
from app.routes import ping, root
from app.routes.recipe import recipe, ingredient, cooking_step
from app.routes.refrigerator import ingredient_detect

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

# Static files configuration
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Public routes
app.include_router(root.router)
app.include_router(ping.router)

# Protected routes
app.include_router(recipe.router, dependencies=[Depends(verify_token)])
app.include_router(ingredient.router, dependencies=[Depends(verify_token)])
app.include_router(cooking_step.router, dependencies=[Depends(verify_token)])
app.include_router(ingredient_detect.router, dependencies=[Depends(verify_token)])
