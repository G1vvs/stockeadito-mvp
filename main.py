# para inicira el venv: .\venv\Scripts\activate
from fastapi import FastAPI, Depends
from routers import inventory, sales, chat, auth
from dependencies import get_current_user
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:3000", # Tu futuro frontend React/Next
    "http://localhost:5173", # Tu futuro frontend Vite
    "*" # (Peligroso en prod, pero útil para desarrollo ahora)
]


# Inicializar la aplicación FastAPI
app = FastAPI(
    title="Stockeadito API",
    version="0.4.0",
    description="Backend modular Routers")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Routers
app.include_router(inventory.router)
app.include_router(sales.router)
app.include_router(chat.router)
app.include_router(auth.router)
# Endpoint raíz de la API
@app.get("/")
async def home():
    return "Hola backend de stockeadito"
# verificamos los datos de owner
@app.get("/me")
#si el guardian get_current_user acepto el usuario. Entramos
def get_my_profile(user = Depends(get_current_user)):
    return {
        "message": "Welcome Back, Owner",
        "user_id": user.id,
        "email": user.email
    }      
#uvicorn main:app --reload