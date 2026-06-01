from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional, Any
from pydantic import BaseModel
# importamos la conexion
from database import supabase
from dependencies import get_current_user
from datetime import datetime

router = APIRouter(
    tags=["Sales & Transactions"]
)

class SaleItem(BaseModel):
    product_id: str
    quantity: int

class SaleRequest(BaseModel):
    items: List[SaleItem]
    payment_method: str = "Efectivo"#debito, credito, efectivo

@router.post("/sales", status_code=status.HTTP_201_CREATED)
def register_sale(sale_data: SaleRequest, user = Depends(get_current_user)):
    """
    1: calcula el total
    2: verifica y descuenta el stock
    3: guarda el registro de venta
    """
    try:
        total_mount = 0
        sale_details = []
        
        for item in sale_data.items:
            # 👇 1. Agregamos "id" al select para capturar la clave primaria 👇
            stock_response = supabase.table("inventario_local")\
            .select("id, stock_actual, precio_venta, catalogo_universal(nombre)")\
            .eq("user_id", user.id)\
            .eq("producto_id", item.product_id)\
            .single()\
            .execute()
            
            # si no existe el producto en el inventario
            if not stock_response.data:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                    detail=f"Producto {item.product_id} no encontrado en tu inventario")
            
            product_data = stock_response.data
            row_id = product_data["id"] # ¡Capturamos el ID exacto de la fila!
            current_stock = product_data["stock_actual"]
            price = product_data["precio_venta"]
            product_name = product_data["catalogo_universal"]["nombre"]

            # validar si hay suficiente stock
            if current_stock < item.quantity:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                    detail=f"Stock insuficiente para {product_name}. Tienes {current_stock}, intentas vender {item.quantity}")
            
            # Calcular subtotal
            subtotal = price * item.quantity
            total_mount += subtotal

            # Actualizar stock (restar venta)
            new_stock = current_stock - item.quantity
            
            # 👇 2. Actualización blindada usando SOLO el id primario 👇
            supabase.table("inventario_local")\
            .update({"stock_actual": new_stock})\
            .eq("id", row_id)\
            .execute()

            # Guardar detalle para el recibo
            sale_details.append({
                "producto": product_name,
                "cantidad": item.quantity,
                "precio_unitario": price,
                "subtotal": subtotal
            })
            
        new_sale = {
            "user_id": user.id,
            "total": total_mount,
            "detalles": sale_details, # guarda detalles en JSON
            "metodo_pago": sale_data.payment_method,
            "created_at": datetime.now().isoformat()
        }
        sale_response = supabase.table("ventas").insert(new_sale).execute()

        return {
            "message":"Venta registrada exitosamente",
            "total": total_mount,
            "new_stock_status": "Stock actualizado",
            "sale_id": sale_response.data[0]["id"]
        }
    except Exception as e:
        print(f"Error de venta: {e}")
        # si es un error http (como falta de stock), lo relanzamos tal cual
        if isinstance(e, HTTPException):
            raise e 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=str(e))
    