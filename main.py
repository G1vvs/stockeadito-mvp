# para inicira el venv: .\venv\Scripts\activate
from fastapi import FastAPI, Depends
from routers import inventory, sales
from dependencies import get_current_user

# Inicializar la aplicación FastAPI
app = FastAPI(
    title="Stockeadito API",
    version="0.4.0",
    description="Backend modular Routers")
#Routers
app.include_router(inventory.router)
app.include_router(sales.router)
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