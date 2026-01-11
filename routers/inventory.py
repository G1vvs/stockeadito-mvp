from fastapi import APIRouter, HTTPException, status, Depends, Body
from typing import List, Optional
from pydantic import BaseModel
# importamos la conexion
from database import supabase
from dependencies import get_current_user, confirmar_pago_activo

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
    product_id: Optional[str] = None
    barcode: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = "General"
    # obligatorios
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
    
@router.post("/inventory", status_code=status.HTTP_200_OK)
def add_to_inventory(item_data: InventoryAdd, user = Depends(confirmar_pago_activo)):
    """
    Lógica Maestra:
    1. Si mandas product_id -> Usamos ese.
    2. Si NO mandas ID, buscamos por CÓDIGO DE BARRA en el Universal.
    3. Si existe -> Usamos ese ID.
    4. Si NO existe -> LO CREAMOS en el Universal -> Usamos el ID nuevo.
    5. Finalmente -> Agregamos a tu inventario local.
    """
    try:
        target_product_id = item_data.product_id

        # CASO A: No mandaron ID, pero mandaron Código de Barra (Escaneo)
        if not target_product_id and item_data.barcode:
            # 1. Buscamos en el Catálogo Universal
            print(f"Buscando código de barra: {item_data.barcode}")
            existing_global = supabase.table("catalogo_universal")\
                .select("id")\
                .eq("codigo_barra", item_data.barcode)\
                .execute()
            
            if existing_global.data:
                # ¡Ya existía! Usamos ese.
                target_product_id = existing_global.data[0]["id"]
                print(f"Encontrado en catálogo global: {target_product_id}")
            else:
                # NO existe. ¡Hay que crearlo para todos! (Crowdsourcing)
                if not item_data.name:
                    raise HTTPException(status_code=400, detail="Para crear un producto nuevo, necesito el nombre")
                
                print(f"Creando nuevo producto global: {item_data.name}")
                new_global_product = {
                    "nombre": item_data.name,
                    "codigo_barra": item_data.barcode,
                    "categoria": item_data.category,
                    "imagen_url": "https://via.placeholder.com/150" # Placeholder por defecto
                }
                global_res = supabase.table("catalogo_universal").insert(new_global_product).execute()
                target_product_id = global_res.data[0]["id"]

        # Si después de todo esto no tenemos ID, error
        if not target_product_id:
            raise HTTPException(status_code=400, detail="Debes enviar product_id O (barcode + nombre)")

        # --- AHORA SÍ: Lógica de Inventario Local (Igual que antes) ---
        
        # 1. Buscamos si TÚ ya lo tienes
        existing_local = supabase.table("inventario_local")\
            .select("*")\
            .eq("user_id", user.id)\
            .eq("producto_id", target_product_id)\
            .execute()

        if existing_local.data:
            # UPDATE
            row_id = existing_local.data[0]["id"]
            current_stock = existing_local.data[0]["stock_actual"]
            new_stock = current_stock + item_data.quantity
            
            response = supabase.table("inventario_local")\
                .update({"stock_actual": new_stock, "precio_venta": item_data.sale_price})\
                .eq("id", row_id)\
                .execute()
            return {"message": "Stock sumado (Producto existente) ", "nuevo_stock": new_stock}
        else:
            # INSERT
            new_local_item = {
                "user_id": user.id,
                "producto_id": target_product_id,
                "stock_actual": item_data.quantity,
                "precio_venta": item_data.sale_price
            }
            response = supabase.table("inventario_local").insert(new_local_item).execute()
            return {"message": "Producto agregado a tu tienda ", "data": response.data}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inventory")
def get_my_inventory(user = Depends(confirmar_pago_activo)):
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
def seed_inventory(user = Depends(confirmar_pago_activo)):
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

class InventoryUpdate(BaseModel):
    stock_actual: int = None
    precio_venta: int = None

# --- RUTAS EXISTENTES ARRIBA ---

# 👇 NUEVA RUTA: EDITAR (PATCH)
@router.patch("/inventory/{item_id}")
def update_inventory_item(item_id: str, update_data: InventoryUpdate, user = Depends(confirmar_pago_activo)):
    """Permite al usuario editar el stock o precio de SU producto"""
    # 1. Validar que el item le pertenece al usuario
    # (El RLS de Supabase ya hace esto, pero es doble seguridad)
    check = supabase.table("inventario_local").select("id").eq("id", item_id).eq("user_id", user.id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Producto no encontrado o no te pertenece.")

    # 2. Preparamos los datos a actualizar (solo los que envió)
    data_to_update = {}
    if update_data.stock_actual is not None:
        data_to_update["stock_actual"] = update_data.stock_actual
    if update_data.precio_venta is not None:
        data_to_update["precio_venta"] = update_data.precio_venta
        
    if not data_to_update:
        return {"msg": "Nada que actualizar"}

    try:
        supabase.table("inventario_local").update(data_to_update).eq("id", item_id).execute()
        return {"msg": "✅ Producto actualizado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 👇 NUEVA RUTA: ELIMINAR (DELETE)
@router.delete("/inventory/{item_id}")
def delete_inventory_item(item_id: str, user = Depends(confirmar_pago_activo)):
    """Elimina un producto del inventario local"""
    try:
        # El RLS asegura que solo borre los suyos
        result = supabase.table("inventario_local").delete().eq("id", item_id).eq("user_id", user.id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Producto no encontrado o no te pertenece.")
        return {"msg": "🗑️ Producto eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
