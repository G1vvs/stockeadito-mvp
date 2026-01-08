# para inicira el venv: .\venv\Scripts\activate
import os
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from supabase import create_client, Client
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Cargar variables de entorno desde el archivo Key.env
load_dotenv('Key.env') # Carga las variables del archivo .env
# Obtener las credenciales de Supabase desde las variables de entorno
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# Verificar que las credenciales estén presentes
if not url or not key:
    raise ValueError("Error: Faltan las llaves en el .env")

# Crear cliente de Supabase con las credenciales
supabase: Client = create_client(url, key)

# Inicializar la aplicación FastAPI
app = FastAPI(
    title= "Stockeadito",
    version= "0.3.0"
)

security = HTTPBearer()

# Definir el esquema de datos para un producto usando Pydantic
class ProductoSchema(BaseModel):
    id: str
    nombre: str
    categoria: Optional[str] = "Sin Categoría"
    codigo_barra: Optional[str] = None
    imagen_url: Optional[str] = None

# esto es para cuando el usuario intenta agregar un item a la tienda
class InventoryAdd(BaseModel):
    product_id: str
    quantity: int
    sale_price: int

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Esta funcion se ejecuta Antes de entrar al endpoint protegido
    valida que el token sea real
    """
    token = credentials.credentials
    try: 
        # le enviamos el token a supabase preguntado si el usuario existe y el token es valido
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid Token")
        #si es valido entras
        return user_response.user
    except Exception as e:
        print(f"error: {e}" )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Could not validate credentials")
# Endpoint raíz de la API
@app.get("/")
async def root():
    return "Hola backend de stockeadito"

# Endpoint para obtener el catálogo de productos
@app.get("/catalog",response_model=List[ProductoSchema])
def get_catalog():
    try:
        # Consultar la tabla 'catalogo_universal' en Supabase, limitando a 20 resultados
        response = supabase.table("catalogo_universal").select("*").limit(20).execute()
        return response.data
    except Exception as e:
        print(f"error: {e}")
        raise HTTPException(status_code=
                            status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al conectar con la base de datos")

@app.get("/catalog/{categoria}",response_model=List[ProductoSchema])
def filtrar_por_categoria(categoria: str):
    try:
        response = supabase.table("catalogo_universal").select("*").eq("categoria", categoria).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# verificamos los datos de owner
@app.get("/me")
#si el guardian get_current_user acepto el usuario. Entramos
def get_my_profile(user = Depends(get_current_user)):
    return {
        "message": "Welcome Back, Owner",
        "user_id": user.id,
        "email": user.email
    }

@app.post("/inventory", status_code=status.HTTP_201_CREATED)
def add_to_inventory(item_data: InventoryAdd, user= Depends(get_current_user)):
    '''
    Recive: product_id, quantity and sale_price
    Action: Insert a new row into 'invetario_local' Linked to the user
    '''
    try:
        new_inventory_item = {
            "user_id": user.id,# From Token
            "producto_id": item_data.product_id,
            "stock_actual": item_data.quantity,  
            "precio_venta": item_data.sale_price
        }
        response = supabase.table("inventario_local").insert(new_inventory_item).execute()
        return {"Message": "Item added to your inventory", "data": response.data}
    except Exception as e:
        print(f"error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
#uvicorn main:app --reload