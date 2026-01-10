# para inicira el venv: .\venv\Scripts\activate
from fastapi import FastAPI, Depends, Request
from routers import inventory, sales, chat, auth, pagos
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
app.include_router(pagos.router)
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

@app.post("/webhook")
async def recibir_notificacion(request: Request):
    # 1. Recibimos los datos que envía Mercado Pago
    datos = await request.json()
    
    # 2. Imprimimos para ver qué nos mandaron (esto saldrá en tu consola)
    print("📩 ¡NOTIFICACIÓN RECIBIDA!", datos)
    
    # 3. Aquí iría la lógica: Buscar en base de datos, enviar email, etc.
    # Por ahora solo veremos el ID del pago.
    query_params = request.query_params
    topic = query_params.get("topic") or datos.get("type")
    id_pago = query_params.get("id") or datos.get("data", {}).get("id")

    if topic == "payment":
        print(f"💰 Se ha recibido información del pago ID: {id_pago}")
        # Aquí luego usaremos el SDK para preguntar el estado real (aprobado/rechazado)
        
    return {"status": "ok"}


#uvicorn main:app --reload