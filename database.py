import os
from fastapi import APIRouter
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables de entorno desde el archivo Key.env
load_dotenv() # Carga las variables del archivo .env
# Obtener las credenciales de Supabase desde las variables de entorno
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
# Verificar que las credenciales estén presentes
if not url or not key:
    raise ValueError("Error: Faltan las llaves en el .env")
# Crear cliente de Supabase con las credenciales
supabase: Client = create_client(url, key)