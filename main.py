import os
#import sys
#import pdb
import bcrypt
import logging
import httpx
import jwt
import json
#import psutil
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from passlib.context import CryptContext
from services.device_service import fetch_devices
from fastapi.security.utils import get_authorization_scheme_param
from routers import auth
from dotenv import load_dotenv
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorClient
from database import user_collection
from models import hash_password, verify_password
from user_schemas import User
from pydantic import BaseModel
from urllib.parse import unquote



# Charging environment variables (file .env)
load_dotenv()

# Mongo DB Configuration
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

# JWT Configuration
DEVICE_API_BASE_URL = os.getenv("DEVICE_API_BASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Fast API & MongoDB Initialization
app = FastAPI(debug=True)
client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB]
user_collection = db.users

# Templates configuration
templates = Jinja2Templates(directory="templates")

# Middleware CORS for front-end requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration of passwords management
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# List of devices and their state
devices = [
    {"id": 1, "name": "Lampe Salon", "status": "off"},
    {"id": 2, "name": "Ventilateur", "status": "on"},
    {"id": 3, "name": "Lampe Cuisine", "status": "off"},
]

# Fonction pour créer un token JWT
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logging.info(f"Token généré : {token}")
    return token

# Fonction pour vérifier le token JWT
async def get_current_user(authorization: str = Header(None)):
    if not authorization:
        logging.error("Header Authorization manquant")
        raise HTTPException(status_code=401, detail="Header Authorization manquant")

    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        logging.info(f"Email extrait du token : {email}")
        if not email:
            raise HTTPException(status_code=401, detail="Token invalide")
        user = await user_collection.find_one({"email": email})
        if not user:
            logging.error("Utilisateur non trouvé")
            raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
        return user
    except JWTError as e:
        logging.error(f"Erreur lors de la validation du token : {e}")
        raise HTTPException(status_code=401, detail="Token invalide")

# Fonction pour récupérer les périphériques depuis une API
async def fetch_devices(token: str):
    if not DEVICE_API_BASE_URL or DEVICE_API_BASE_URL == "http://127.0.0.1:8000":
        # Si l'URL de l'API n'est pas configurée, utilisez la liste locale
        logging.warning("DEVICE_API_BASE_URL non configurée, retour des devices locaux")
        return devices
    try:
        url = DEVICE_API_BASE_URL.rstrip("/") + "/devices"  # Supprime les slashs inutiles
        headers = {"Authorization": f"Bearer {token}"}
        logging.info(f"Fetching devices from URL: {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
        print(response.status_code)
        print(response.json())
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Erreur API : {response.status_code} {response.text}")
    
    except httpx.RequestError as e:
        logging.error(f"Erreur lors de l'appel à l'API : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'appel à l'API : {str(e)}")
    except httpx.HTTPStatusError as e:
        logging.error(f"Erreur HTTP : {str(e)}")
        raise HTTPException(status_code=response.status_code, detail=f"Erreur API : {e}")


########## Routes ########

# Registration page
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Affiche la page d'inscription avec un formulaire d'inscription.
    """
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register(email: str = Form(...), password: str = Form(...)):
    # Vérifier si l'utilisateur existe déjà
    existing_user = await user_collection.find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hacher le mot de passe
    hashed_password = pwd_context.hash(password)

    # Enregistrer l'utilisateur
    await user_collection.insert_one({"email": email, "password": hashed_password})

    # Générer le token JWT
    access_token = create_access_token(data={"sub": email})

    # Redirection vers la page des devices après l'enregistrement
    #return RedirectResponse(url="/devices", status_code=302)

    # Redirection vers /devices avec le token JWT dans les query params
    return RedirectResponse(url=f"/devices?token={access_token}", status_code=302)

# Connexion page
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Connexion processing
@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    db_user = await user_collection.find_one({"email": email})
    if not db_user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    if not verify_password(password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    
    # Log connection with IP address
    #client_ip = request.client.host
    #await log_connection(email, client_ip)

    # Last connexion update
    await user_collection.update_one(
        {"email": email},  # Filtre par email
        {"$set": {"last_login": datetime.now()}}  # Mise à jour du champ last_login
    )

    access_token = create_access_token(data={"sub": email})
    return RedirectResponse(url=f"/devices?token={access_token}", status_code=302)

# Page d'accueil
#@app.get("/", response_class=HTMLResponse)
#async def render_home(request: Request):
#    return templates.TemplateResponse("index.html", {"request": request})
#async def fetch_devices():
#    try:
#        async with httpx.AsyncClient() as client:
#            response = await client.get(f"{DEVICE_API_BASE_URL}/list")
#            response.raise_for_status()
#            return response.json()
#    except httpx.RequestError as e:
#        logging.error(f"Error fetching devices: {e}")
#        raise HTTPException(status_code=500, detail="Error fetching devices")


# Devices page
@app.get("/devices", response_class=HTMLResponse)
async def devices_page(request: Request, token: str = None):
    if not token:
        authorization = request.headers.get("Authorization")
        if authorization:
            scheme, token = get_authorization_scheme_param(authorization)
    if not token:
        raise HTTPException(status_code=400, detail="Token manquant")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Token invalide")
        
        # Récupération de l'utilisateur
        user = await user_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="Utilisateur non trouvé")

        # Appel à fetch_devices
        devices_list = await fetch_devices(token)
        return templates.TemplateResponse("devices.html", {"request": request, "devices": devices_list, "user": user})
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")
    
async def get_devices():
    return devices


async def get_devices(token: str = Depends(oauth2_scheme)):
    try:
        user = verify_token(token)
        return {"message": "Devices fetched successfully", "user": user}
    except HTTPException as e:
        raise e
    

# Route pour basculer l'état d'un périphérique
@app.post("/devices/{device_name}/toggle")
async def toggle_device(device_name: str):
    for device in devices:
        if device["name"] == device_name:
            device["status"] = "on" if device["status"] == "off" else "off"
            return {"name": device_name, "status": device["status"]}
    raise HTTPException(status_code=404, detail="Device not found")

# Afficher les utilisateurs inscrits
@app.get("/users.html", response_class=HTMLResponse)
async def users_html(request: Request):
    """
    Renvoie la page users.html pour naviguer vers les utilisateurs et connexions.
    """
    return templates.TemplateResponse("users.html", {"request": request})

@app.get("/users", response_class=HTMLResponse)
async def list_users(request: Request, user: dict = Depends(get_current_user)):
    logging.info(f"User authenticated: {user}")
    try:
        # Récupération des utilisateurs depuis MongoDB
        users = await user_collection.find({}, {"_id": 0, "email": 1}).to_list(100)  # Ne récupérer que les emails
        if not users:
            raise HTTPException(status_code=404, detail="Aucun utilisateur trouvé")

        # Rendu du template avec les utilisateurs
        return templates.TemplateResponse(
            "users.html",
            {"request": request, "users": users},
        )
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des utilisateurs : {e}")
        return JSONResponse(
            {"message": "Erreur lors de la récupération des utilisateurs."},
            status_code=500,
        )




# Afficher les connexions (historique)
@app.get("/connections", response_class=HTMLResponse)
async def list_connections(request: Request, user: dict = Depends(get_current_user)):
    try:
        # Récupération des connexions depuis MongoDB
        connections = await db.connections.find({}, {"_id": 0, "username": 1, "login_time": 1, "ip_address": 1}).to_list(100)
        if not connections:
            connections = []  # Si aucune connexion trouvée, renvoyer un tableau vide

        # Rendu du template avec les connexions
        return templates.TemplateResponse(
            "users.html",
            {"request": request, "connections": connections},
        )
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des connexions : {e}")
        return JSONResponse(
            {"message": "Erreur lors de la récupération des connexions."},
            status_code=500,
        )





######################

#######Connexion###########

# IP adress and connexion time
from datetime import datetime

# Exemple d'enregistrement d'une connexion avec date et heure
async def log_connection(username: str, ip_address: str):
    connection_data = {
        "username": username,
        "ip_address": ip_address,
        "login_time": datetime.now(),  # Heure de la connexion
        "date_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Date et heure formatée
    }
    await db.connections.insert_one(connection_data)

# Simuler une base de données d'utilisateurs
#fake_users_db = {
 #   "admin": {
  #      "username": "admin",
   #     "hashed_password": pwd_context.hash("password"),
    #    "disabled": False,
    #}
#}

# Middleware pour gérer les erreurs
@app.middleware("http")
async def error_handling_middleware(request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logging.error(f"Erreur : {str(e)}")
        return JSONResponse(
            status_code=500, content={"message": "Une erreur est survenue."}
        )



# Fonction utilitaire pour vérifier un mot de passe
def verify_password(plain_password, hashed_password):
    #return pwd_context.verify(plain_password, hashed_password)
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

# Fonction utilitaire pour vérifier le token
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Not authenticated")


# Fonction pour récupérer un utilisateur
#def get_user(username: str):
 #   user = fake_users_db.get(username)
  #  return user



# Route to get a token (login)
@app.post("/token")
async def login_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await db.users.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}

# Route protégée (exemple)
@app.get("/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    return {"message": f"Hello, {current_user['username']}! This is a protected route."}




# page index2
#@app.get("/index2", response_class=HTMLResponse)
#async def render_index2(request: Request):
#    return templates.TemplateResponse("index2.html", {"request": request})

# page stats
@app.get("/stats", response_class=HTMLResponse)
async def render_stats_page(request: Request):
    return templates.TemplateResponse("stats.html", {"request": request})

# page stats2
#@app.get("/stats2", response_class=HTMLResponse)
#async def render_stats2_page(request: Request):
#    return templates.TemplateResponse("stats2.html", {"request": request})


#app.include_router(auth.router, prefix="/auth")


# Route pour définir explicitement l'état d'un périphérique
@app.put("/devices/{device_name}/set")
async def set_device_status(device_name: str, status: bool):
    if device_name in devices:
        devices[device_name]["status"] = status
        return {"message": f"{device_name} status set to {status}"}
    else:
        return {"error": "Device not found"}, 404

#code de devide
@app.post("/devices/{device_name}/toggle")
async def toggle_device(device_name: str):
    if device_name in devices:
        devices[device_name]["status"] = not devices[device_name]["status"]
        return {"message": f"{device_name} toggled", "status": devices[device_name]["status"]}
    else:
        raise HTTPException(status_code=404, detail="Device not found")



##@app.get("/devices/list")
##async def list_devices():
##    devices = await fetch_devices()
##    return {"devices": devices}

# Configuration of the journal
logging.basicConfig(filename="app.log", level=logging.INFO)

