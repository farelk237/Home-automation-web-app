import os
#import sys
#import pdb
import logging
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.device_service import fetch_devices
from routers import auth
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi import Request
from dotenv import load_dotenv
from fastapi import HTTPException



app = FastAPI(debug=True)

#pdb.set_trace()

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def render_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

async def fetch_devices():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{DEVICE_API_BASE_URL}/list")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logging.error(f"Error fetching devices: {e}")
        raise HTTPException(status_code=500, detail="Error fetching devices")



load_dotenv()  # Charge les variables d'environnement du fichier .env

DEVICE_API_BASE_URL = os.getenv("DEVICE_API_BASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")


app.include_router(auth.router, prefix="/auth")

# Configuration du journal
logging.basicConfig(filename="app.log", level=logging.INFO)

@app.get("/devices/list")
async def list_devices():
    devices = await fetch_devices()
    return {"devices": devices}

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
    
# Middleware CORS for front-end requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# List of devices and their state
devices = {
    "lamp1": {"name": "lamp1", "status": True},
    "lamp2": {"name": "lamp2", "status": False},
    "Fan": {"name": "Fan", "status": False}
}

@app.get("/devices")
async def get_devices():
    return devices

# Route pour basculer l'état d'un périphérique
@app.post("/devices/{device_name}/toggle")
async def toggle_device(device_name: str):
    if device_name in devices:
        devices[device_name]["status"] = not devices[device_name]["status"]
        return {"message": f"{device_name} toggled", "status": devices[device_name]["status"]}
    else:
        raise HTTPException(status_code=404, detail="Device not found")

# Route pour définir explicitement l'état d'un périphérique
@app.put("/devices/{device_name}/set")
async def set_device_status(device_name: str, status: bool):
    if device_name in devices:
        devices[device_name]["status"] = status
        return {"message": f"{device_name} status set to {status}"}
    else:
        return {"error": "Device not found"}, 404
