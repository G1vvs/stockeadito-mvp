from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from pydantic import BaseModel
# importamos la conexion
from database import supabase
from dependencies import get_current_user

router = APIRouter(
    prefix=("/api"),
    tags=["Inventory & Catalog"]
)

# -- Models
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

# Endpoint para obtener el catálogo de productos
@router.get("/catalog",response_model=List[ProductoSchema])
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

@router.get("/catalog/{categoria}",response_model=List[ProductoSchema])
def filtrar_por_categoria(categoria: str):
    try:
        response = supabase.table("catalogo_universal").select("*").eq("categoria", categoria).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
@router.post("/inventory", status_code=status.HTTP_201_CREATED)
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

@router.get("/inventory")
def get_my_inventory(user = Depends(get_current_user)):
    """
    Retourn ONLY the items belonging to be logged-in user.
    we also do a 'join' to fetch the product name
    """
    try:
        response = supabase.table("inventario_local")\
        .select("*, catalogo_universal(nombre, categoria, imagen_url)")\
        .eq("user_id", user.id)\
        .execute()
        return response.data
    except Exception as e:
        print(f"error gettin inventory: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
@router.post("/seed", status_code=status.HTTP_201_CREATED)
def seed_inventory(user = Depends(get_current_user)):
    """
    Action: Copies ALL products from 'catalogo_universal' to 'inventario_local'
    for the current user. 
    Warning: If run twice, it might duplicate items (unless handled).
    """
    try: 
        existing_stock = supabase.table("inventario_local").select("id").eq("user_id",user.id).limit(1).execute()
        if len(existing_stock.data) > 0:
            return {"message": " Inventory already initialized. Skipping seed to avoid duplicates."}
        catalog_response = supabase.table("catalogo_universal").select("id").execute()
        global_products = catalog_response.data

        if not global_products:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Global catalog is empty!")
        
        inventory_entries = []
        for product in global_products:
            entry = {
                "user_id": user.id,            # The owner (You)
                "producto_id": product["id"],  # The product
                "stock_actual": 0,             # Start with 0 stock (User must count later)
                "stock_minimo": 5,             # Default alert threshold
                "precio_venta": 0              # Default price (User must set it)
            }
            inventory_entries.append(entry)

        # 4. Execute Bulk Insert (One shot)
        # This is much faster than inserting one by one
        insert_response = supabase.table("inventario_local").insert(inventory_entries).execute()

        return {
            "message": f"Success! {len(insert_response.data)} products added to your inventory.",
            "total_items": len(insert_response.data)
        }

    except Exception as e:
        print(f"Seed Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


