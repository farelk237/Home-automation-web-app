from pymongo import MongoClient

try:
    # Connexion à MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client.test_database  # Exemple de base de données

    # Vérifier la connexion en listant les bases de données
    dbs = client.list_database_names()
    print("Connexion réussie à MongoDB !")
    print("Bases de données disponibles :", dbs)

except Exception as e:
    print("Erreur de connexion à MongoDB :", e)
