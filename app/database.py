from motor.motor_asyncio import AsyncIOMotorClient

from app.config import MONGODB_URL

client = AsyncIOMotorClient(MONGODB_URL)
db = client.deening
recipe_collection = db.recipes
cooking_step_collection = db.cooking_steps
ingredients_info_collection = db.ingredients_info
refrigerator_collection = db.refrigerator
preference_collection = db.preferences
