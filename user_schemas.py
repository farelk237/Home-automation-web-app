from pydantic import BaseModel, EmailStr
from datetime import datetime
class User(BaseModel):
    email: EmailStr
    password: str
    last_login: datetime  # Dernière connexion de l'utilisateur
###########validation des donnees