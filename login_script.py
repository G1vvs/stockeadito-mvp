import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('Key.env')

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# Cambia esto por el email y pass que creaste recién
email = "giovanni@stockeadito.com"
password = "Stockeadito2025!" 

try:
    session = supabase.auth.sign_in_with_password({"email": email, "password": password})
    print("\n✅ LOGIN EXITOSO!")
    print("---------------------------------------------------")
    print("TU TOKEN DE ACCESO (Copia todo esto):")
    print(session.session.access_token)
    print("---------------------------------------------------")
except Exception as e:
    print(f"❌ Error: {e}")