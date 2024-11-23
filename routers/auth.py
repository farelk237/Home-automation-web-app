from fastapi import APIRouter

router = APIRouter()

@router.post("/login")
async def login(username: str, password: str):
    # Votre logique ici
    return {"message": "Connexion réussie"}
