import mercadopago
import os
from fastapi import APIRouter, HTTPException, Request, Response,Depends
from pydantic import BaseModel
from dotenv import load_dotenv
from database import supabase
from dependencies import get_current_user

load_dotenv()
router = APIRouter(tags=["Pagos"])

ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
ACCESS_WEB = os.getenv("WEBHOOK_URL")

if not ACCESS_TOKEN:
    # Esto es solo para que no falle en tu PC si no has configurado la variable de entorno localmente
    # Pero OJO: No subas este archivo con tu token real escrito aquí abajo si es público.
    # Lo ideal es dejarlo vacío o configurar tu .env local.
    print("⚠️ ADVERTENCIA: Usando token temporal o vacío")
    ACCESS_TOKEN = "TU_TOKEN_AQUI_SOLO_PARA_PRUEBAS_LOCALES"

sdk = mercadopago.SDK(ACCESS_TOKEN)

class SolicitudPago(BaseModel):
    user_id: str
    email_usuario: str
    precio: int = 5000

@router.post("/pagar/crear-link")
def crear_pago(datos: SolicitudPago, user_autenticado = Depends(get_current_user)):
    user_id = user_autenticado.id
    user_email = user_autenticado.email
    print(f"💰 Creando pago para usuario verificado: {user_email} (ID: {user_id})")

    preference_data = {
        "items": [
            {
                "id": "suscripcion_mensual",
                "title": "Suscripción Stockeadito",
                "quantity": 1,
                "unit_price": float(datos.precio),
                "currency_id": "CLP"
            }
        ],
        "payer": {"email": user_email},
        "external_reference": user_id, # <--- VINCLULAMOS EL PAGO AL USUARIO
        "back_urls": {
            "success": "https://tu-sitio.com/success",
            "failure": "https://tu-sitio.com/failure",
            "pending": "https://tu-sitio.com/pending"
        },
        "auto_return": "approved",
        "notification_url": "WEBHOOK_URL"
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        response_body = preference_response.get("response")
        return {
            "url_pago": response_body["init_point"], 
            "id_preferencia": response_body["id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def recibir_webhook(request: Request):
    datos = await request.json()
    
    # Extraer ID de pago dinámico
    payment_id = datos.get("data", {}).get("id") or request.query_params.get("id")
    topic = datos.get("type") or datos.get("topic")

    if topic == "payment" and payment_id:
        # 1. ¿Ya existe este pago? (Evitar duplicidad)
        check = supabase.table("pagos_mp").select("id_mp").eq("id_mp", str(payment_id)).execute()
        if check.data:
            return {"status": "ok"} # Ya procesado, no hacemos nada

        # 2. Consultar a Mercado Pago
        payment_info = sdk.payment().get(payment_id)
        res = payment_info["response"]
        
        if res.get("status") == "approved":
            user_id = res.get("external_reference") # El UUID de Supabase que enviamos
            monto = res.get("transaction_amount")
            
            # 3. ACTUALIZACIÓN MULTI-TABLA EN SUPABASE
            # A. Registrar el pago
            supabase.table("pagos_mp").insert({
                "id_mp": str(payment_id),
                "user_id": user_id,
                "email_pago": res["payer"]["email"],
                "monto": monto,
                "estado": "approved"
            }).execute()

            # B. Actualizar Perfil a Premium 
            supabase.table("profiles").update({
                "subscription_status": "premium"
            }).eq("id", user_id).execute()

            # C. Actualizar Tabla Suscripciones 
            # Calculamos 30 días a partir de hoy
            from datetime import datetime, timedelta
            fin_periodo = (datetime.now() + timedelta(days=30)).isoformat()
            
            supabase.table("suscripciones").upsert({
                "user_id": user_id,
                "estado": "activo",
                "fin_periodo": fin_periodo
            }).execute()

            print(f"🚀 Usuario {user_id} ahora es PREMIUM")

    return {"status": "ok"}