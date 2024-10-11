from motor.motor_asyncio import AsyncIOMotorClient

from app.config import MONGODB_URL

client = AsyncIOMotorClient(MONGODB_URL)
db = client.deening
recipe_collection = db.recipes
cooking_step_collection = db.cooking_steps
ingredient_collection = db.ingredients
refrigerator_collection = db.refrigerator
