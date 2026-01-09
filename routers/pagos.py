import mercadopago
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
router = APIRouter(tags=["Pagos"])

ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

if not ACCESS_TOKEN:
    # Esto es solo para que no falle en tu PC si no has configurado la variable de entorno localmente
    # Pero OJO: No subas este archivo con tu token real escrito aquí abajo si es público.
    # Lo ideal es dejarlo vacío o configurar tu .env local.
    print("⚠️ ADVERTENCIA: Usando token temporal o vacío")
    ACCESS_TOKEN = "TU_TOKEN_AQUI_SOLO_PARA_PRUEBAS_LOCALES"

sdk = mercadopago.SDK(ACCESS_TOKEN)

class SolicitudPago(BaseModel):
    email_usuario: str
    precio: int = 5000

@router.post("/pagar/crear-link")
def crear_pago(datos: SolicitudPago):
    
    print(f"💰 Intentando crear pago para: {datos.email_usuario} por ${datos.precio}")

    preference_data = {
        "items": [
            {
                "id": "suscripcion_mensual",
                "title": "Suscripción Stockeadito",
                "quantity": 1,
                "unit_price": float(datos.precio), # Convertimos a float
                "currency_id": "CLP"
            }
        ],
        "payer": {
            "email": datos.email_usuario
        },
        "back_urls": {
            "success": "https://www.google.cl",
            "failure": "https://www.google.cl",
            "pending": "https://www.google.cl"
        },
        "auto_return": "approved"
    }

    try:
        # Llamamos a Mercado Pago
        preference_response = sdk.preference().create(preference_data)
        
        # 👇 DIAGNÓSTICO IMPORTANTE
        status = preference_response.get("status")
        response_body = preference_response.get("response")

        # Si el estatus no es 200 (OK) o 201 (Creado), hubo error
        if status not in [200, 201]:
            print("\n❌ ERROR DE MERCADO PAGO DETALLADO:")
            print(response_body) # <--- ESTO ES LO QUE NECESITO VER
            raise Exception(f"Mercado Pago respondió estatus {status}")

        return {
            "msg": "✅ Link de pago generado", 
            "url_pago": response_body["init_point"], 
            "id_preferencia": response_body["id"]
        }
        
    except Exception as e:
        print(f"\n🔥 EXCEPCIÓN EN TERMINAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))