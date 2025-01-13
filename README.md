# Home Automation Web App

## 0. Objective
The goal of this project is to develop a functional web application with a secure API for managing users and connected devices. The application allows centralized and interactive remote control of devices such as lamps and fans, while ensuring secure access through user accounts.

## 1. Features
- User registration with secure password handling (hashed passwords).
- Login with JWT authentication.
- View the list of users.
- Connection history tracking.
- Display available devices (lamps, fans, etc.).
- Interact with devices (turn on/off).
- Persistent device states using MongoDB.

## 2. Prerequisites
- Docker and Docker-Compose installed.
- Python 3.9 or higher (if running locally without Docker).

## 3. Local Deployment
### Using Docker
1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo-name.git
   cd your-repo-name
2. Build and start the application with Docker:
   docker-compose up --build

3. Access the application at:
Frontend: http://127.0.0.1:8000/
API Documentation: http://127.0.0.1:8000/docs

Without Docker (We never know)

1. Install dependencies:
pip install -r requirements.txt

2. Start the server:
uvicorn src.main:app --host 0.0.0.0 --port 8000

3. Access the application at:
Frontend: http://127.0.0.1:8000/
API Documentation: http://127.0.0.1:8000/docs
   
