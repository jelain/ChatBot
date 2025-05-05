from fastapi import FastAPI, Request 
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.llm.model import llm, get_llm_response
from backend.core.db import SessionLocal, User
from backend.core.auth_utils import hash_password, verify_password
import uvicorn


app = FastAPI()

# Autoriser les requêtes du frontend Vue.js (localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialiser le LLM
llm()

# Route principale du chatbot
@app.get("/llm/{prompt}")
async def get_response(prompt: str, request: Request):
    user_email = request.headers.get("X-User-Email", "default")
    session_id = request.headers.get("X-Session-ID", "Session 1")
    try:
        answer = get_llm_response(prompt, user_email=user_email, session_name=session_id)
        return {"answer": answer}
    except Exception as e:
        return {"error": str(e)}

# Authentification
class AuthData(BaseModel):
    email: str
    password: str

@app.post("/login")
async def login(data: AuthData):
    db = SessionLocal()
    user = db.query(User).filter(User.email == data.email).first()
    if user and verify_password(data.password, user.hashed_password):
        return {"success": True}
    return {"success": False, "message": "Identifiants invalides"}

@app.post("/register")
async def register(data: AuthData):
    db = SessionLocal()
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        return {"success": False, "message": "Utilisateur déjà existant"}
    new_user = User(email=data.email, hashed_password=hash_password(data.password))
    db.add(new_user)
    db.commit()
    return {"success": True}

# Lancement du serveur
if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)



