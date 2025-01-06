from pymongo import MongoClient
#from motor.motor_asyncio import AsyncMongoClient

# Connexion à MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["user_db"]  # Nom de la base de données
user_collection = db["users"]  # Nom de la collection

#client = AsyncIOMotorClient(MONGO_URI)
#db = client[MONGO_DB]
#user_collection = db.users
