import os
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Cargar el archivo .env ANTES de pedir las variables
load_dotenv(override=True)
# 2. Extraer las variables
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

# 3. Inicializar Supabase
if not url or not key:
    raise ValueError("Faltan las variables de entorno de Supabase")

supabase: Client = create_client(url, key)