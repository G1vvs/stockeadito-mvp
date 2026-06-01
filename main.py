# main.py
import os
from fastapi import FastAPI, Depends, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dependencies import get_current_user

# Routers
from routers import inventory, sales, chat, auth, pagos

# ==========================================
# 📍 CONFIGURACIÓN DE RUTAS
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
ASSETS_DIR = os.path.join(FRONTEND_DIR, "assets")

app = FastAPI(title="Stockeadito API", version="1.0.0")

# ==========================================
# ⚙️ MIDDLEWARES & ASSETS
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ FIX: Rutas de JS y CSS con headers anti-caché
# Deben ir ANTES del app.mount para que FastAPI las procese primero
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
}

@app.get("/assets/js/{filename}")
async def serve_js(filename: str):
    return FileResponse(
        path=os.path.join(ASSETS_DIR, "js", filename),
        headers=NO_CACHE_HEADERS
    )

@app.get("/assets/css/{filename}")
async def serve_css(filename: str):
    return FileResponse(
        path=os.path.join(ASSETS_DIR, "css", filename),
        headers=NO_CACHE_HEADERS
    )

# El resto de assets (imágenes, etc.) se sirven normal
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# ==========================================
# 🔗 ROUTERS API
# ==========================================
app.include_router(inventory.router)
app.include_router(sales.router)
app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(pagos.router)

# ==========================================
# 📄 VISTAS HTML (FRONTEND)
# ==========================================

@app.get("/")
async def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/dashboard")
async def dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))

@app.get("/pagos.html")
async def pagos_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "pagos.html"))

# ==========================================
# 👤 UTILIDADES & WEBHOOKS
# ==========================================

@app.get("/me")
def get_my_profile(user = Depends(get_current_user)):
    return {"user_id": user.id, "email": user.email}