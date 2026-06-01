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
    
    # 👇 ESTE ES EL DETECTOR 👇
    print("🚨🚨🚨 VERSIÓN NUEVA CARGADA 🚨🚨🚨") 
    print(f"💰 Creando pago para usuario verificado: {user_email} (ID: {user_id})")

    preference_data = {
        "items": [
            {
                "id": "suscripcion_mensual",
                "title": "Suscripción Stockeadito Premium",
                "quantity": 1,
                "unit_price": float(datos.precio),
                "currency_id": "CLP"
            }
        ],
        "payer": {"email": user_email},
        "external_reference": user_id, 
        
        # 👇 Usamos Ngrok también aquí para que MercadoPago no nos bloquee 👇
        "back_urls": {
            "success": "https://unstilled-keith-unrarefied.ngrok-free.dev/dashboard",
            "failure": "https://unstilled-keith-unrarefied.ngrok-free.dev/pagos.html",
            "pending": "https://unstilled-keith-unrarefied.ngrok-free.dev/pagos.html"
        },
        "auto_return": "approved",
        "notification_url": "https://unstilled-keith-unrarefied.ngrok-free.dev/webhook"
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        print("🔍 Respuesta de MercadoPago:", preference_response)
        
        if preference_response.get("status") == 201 or preference_response.get("status") == 200:
            response_body = preference_response.get("response")
            return {
                "url_pago": response_body["init_point"], 
                "id_preferencia": response_body["id"]
            }
        else:
            mensaje_error = preference_response.get("response", {}).get("message", "Error desconocido")
            print(f"❌ MercadoPago rechazó el pago: {mensaje_error}")
            raise ValueError(f"Rechazado por MP: {mensaje_error}")
            
    except Exception as e:
        print(f"🔥 Error en el código: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def recibir_webhook(request: Request):
    try:
        datos = await request.json()
    except:
        datos = {}

    # 1. Extracción a prueba de fallos (MercadoPago manda los IDs de muchas formas)
    payment_id = request.query_params.get("data.id") or request.query_params.get("id") or datos.get("data", {}).get("id")
    topic = request.query_params.get("type") or request.query_params.get("topic") or datos.get("type") or datos.get("action")

    # Si no es un pago, ignoramos silenciosamente
    if not payment_id or topic not in ["payment", "payment.created"]:
        return Response(status_code=200) 

    try:
        print(f"✅ Webhook recibido - Intentando procesar Pago ID: {payment_id}")
        
        # 2. Consultar a MercadoPago de forma segura
        payment_info = sdk.payment().get(payment_id)
        res = payment_info.get("response", {})
        
        if res.get("status") == "approved":
            user_id = res.get("external_reference")
            
            # Verificamos que tengamos al usuario antes de tocar la base de datos
            if not user_id:
                print("⚠️ Pago aprobado pero sin ID de usuario (external_reference vacío).")
                return Response(status_code=200)

            monto = res.get("transaction_amount", 0)
            payer_info = res.get("payer") or {}
            email_pago = payer_info.get("email", "desconocido")
            
            print(f"💾 Guardando datos en Supabase para el usuario: {user_id}")

            # 3. ACTUALIZACIÓN DE BASE DE DATOS
            supabase.table("pagos_mp").upsert({
                "id_mp": str(payment_id), 
                "user_id": user_id,
                "email_pago": email_pago, 
                "monto": monto, 
                "estado": "approved"
            }).execute()

            # 👇 APLICANDO TU IDEA DEL BOOLEANO 👇
            # Asegúrate de que en Supabase cambiaste la columna a tipo bool (True/False)
            supabase.table("profiles").update({
                "subscription_status": "premium"  
            }).eq("id", user_id).execute()

            from datetime import datetime, timedelta
            fin_periodo = (datetime.now() + timedelta(days=30)).isoformat()
            supabase.table("suscripciones").upsert({
                "user_id": user_id, 
                "estado": "activo", 
                "fin_periodo": fin_periodo
            }).execute()

            print(f"🚀 ¡ÉXITO! Base de datos actualizada correctamente.")
            
        return Response(status_code=200)

    except Exception as e:
        # Aquí atrapamos el error exacto sin crashear el servidor
        print(f"🔥 ERROR FATAL EN EL CÓDIGO/BASE DE DATOS: {str(e)}")
        # Devolvemos 200 de todas formas para que MercadoPago no tumbe el servidor con reintentos
        return Response(status_code=200)