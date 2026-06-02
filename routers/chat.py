import json
import os
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from openai import OpenAI
from dependencies import get_current_user, confirmar_pago_activo
from database import supabase
from datetime import datetime, date
import shutil 
from fastapi import UploadFile, File

# Iniciamos cliente
client = OpenAI()

router = APIRouter(
    prefix="/api",
    tags=["AI Brain"]
)

# --- 1. FUNCIONES DE MEMORIA (NUEVO) ---
def get_chat_history(user_id: str, limit: int = 6):
    """Recupera los últimos mensajes para darle contexto a la IA"""
    try:
        # Traemos los últimos 6 mensajes (descendiente para obtener los recientes)
        response = supabase.table("chat_history")\
            .select("role, content")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        # Invertimos la lista para que queden en orden cronológico (Viejo -> Nuevo)
        history = response.data[::-1]
        return history
    except Exception as e:
        print(f"Error recuperando historial: {e}")
        return []

def save_chat_message(user_id: str, role: str, content: str):
    """Guarda un mensaje en la base de datos"""
    try:
        if content: # Solo guardamos si hay texto
            supabase.table("chat_history").insert({
                "user_id": user_id,
                "role": role,
                "content": content
            }).execute()
    except Exception as e:
        print(f"Error guardando mensaje: {e}")

# --- 2. SISTEMA Y PROMPT ---
def load_system_prompt():
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, "prompts", "stockeadito_system.md")
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        return "Eres un asistente útil de ventas."

#busqueda inteligente

def tool_ver_mis_productos(user_id: str):
    """Muestra todo el inventario del usuario"""
    inv = supabase.table("inventario_local")\
        .select("producto_id, stock_actual, precio_venta")\
        .eq("user_id", user_id)\
        .execute()
    
    if not inv.data:
        return "Tu inventario está vacío. ¡Empieza a agregar productos!"
    
    lista_ids = [item["producto_id"] for item in inv.data]
    
    nombres = supabase.table("catalogo_universal")\
        .select("id, nombre")\
        .in_("id", lista_ids)\
        .execute()
        
    mapa_nombres = {n["id"]: n["nombre"] for n in nombres.data}
    
    # CAMBIO AQUÍ: Formato más explícito para que la IA no ignore el precio
    reporte = "📋 **REPORTE DE INVENTARIO:**\n"
    for item in inv.data:
        nombre = mapa_nombres.get(item["producto_id"], "Producto Desconocido")
        stock = item["stock_actual"]
        precio = item["precio_venta"]
        # Usamos un formato de lista claro
        reporte += f"- {nombre} | Stock: {stock} | Precio: ${precio}\n"
        
    return reporte

def buscar_producto_id(nombre_vago: str, user_id: str):
    """
    Búsqueda inteligente V5: Prioridad por coincidencia de Sinónimos y Nombres.
    Evita la creación de duplicados cuando hay múltiples resultados parecidos.
    """
    termino = nombre_vago.strip().lower()
    print(f"🔎 Buscando término original: '{termino}'")

    # --- 1. SUB-FUNCIÓN: SINGULARIZADOR ---
    def singularizar(palabra):
        if palabra.endswith("es"): return palabra[:-2]
        if palabra.endswith("s"): return palabra[:-1]
        return palabra

    # --- 2. SUB-FUNCIÓN: PROCESAR RESULTADOS (MEJORADA) ---
    def procesar_resultados(data, termino_busqueda):
        if not data: return None
        
        # Caso A: Solo hay uno, no hay duda.
        if len(data) == 1:
            return data[0]["id"], data[0]["nombre"], 0, 0

        # Caso B: Hay varios. Buscamos si uno coincide "mejor" con el término.
        # Esto soluciona el problema de "Coca-Cola 3L" vs "Coca-Cola Original 3L"
        coincidencias_exactas = []
        for p in data:
            nombre = p.get('nombre', '').lower()
            sinonimos = p.get('sinonimos', '')
            sinonimos = sinonimos.lower() if sinonimos else ""
            
            # Si el término exacto está en el nombre o en los sinónimos
            if termino_busqueda in nombre or termino_busqueda in sinonimos:
                coincidencias_exactas.append(p)

        # Si después de filtrar solo nos queda uno que encaja perfecto, lo elegimos.
        if len(coincidencias_exactas) == 1:
            print(f"🎯 Coincidencia única tras filtrado: {coincidencias_exactas[0]['nombre']}")
            return coincidencias_exactas[0]["id"], coincidencias_exactas[0]["nombre"], 0, 0

        # Caso C: Sigue habiendo ambigüedad real.
        nombres_encontrados = [p['nombre'] for p in data]
        print(f" ⚠️ Ambigüedad detectada entre: {nombres_encontrados}")
        lista_str = ", ".join(nombres_encontrados)
        return None, f"❌ Encontré varios productos: {lista_str}. ¿Cuál de estos es?", 0, 0

    # --- 3. SUB-FUNCIÓN: EJECUTAR BÚSQUEDA ---
    def ejecutar_busqueda(termino_busqueda):
        t = f"%{termino_busqueda}%"
        # [cite_start]Buscamos en nombre O sinónimos [cite: 16]
        filtro_or = f"nombre.ilike.{t},sinonimos.ilike.{t}"
        
        return supabase.table("catalogo_universal")\
            .select("id, nombre, sinonimos")\
            .or_(filtro_or)\
            .limit(10)\
            .execute()

    # --- FLUJO PRINCIPAL ---

    # INTENTO 1: Búsqueda Flexible (reemplazando espacios por comodines)
    termino_flexible = termino.replace(" ", "%")
    response = ejecutar_busqueda(termino_flexible)
    
    if response.data:
        resultado = procesar_resultados(response.data, termino)
        if resultado is not None and (resultado[0] is not None or "Encontré varios" in str(resultado[1])):
            prod_id, prod_nombre, _, _ = resultado
            if prod_id is None: return resultado # Es el mensaje de ambigüedad
        else:
            # Si procesar_resultados no dio un ID claro, probamos el Plan B
            response.data = [] 

    if not response.data:
        # INTENTO 2: Plan B (Raíz Singularizada)
        palabras = termino.split(" ")
        primera_palabra = palabras[0]
        raiz = singularizar(primera_palabra) 
        
        print(f"🔄 Intento 2: Buscando raíz '{raiz}'")
        
        if len(raiz) >= 3:
            response = ejecutar_busqueda(raiz)
            resultado_b = procesar_resultados(response.data, termino)
            if not resultado_b: return None, None, 0, 0
            if resultado_b[0] is None: return resultado_b # Mensaje de ambigüedad
            
            prod_id, prod_nombre, _, _ = resultado_b
        else:
            return None, None, 0, 0

    # 4. Búsqueda en Inventario Local del Usuario
    print(f"✅ Match elegido: {prod_nombre} (ID: {prod_id})")
    
    inv = supabase.table("inventario_local")\
        .select("stock_actual, precio_venta")\
        .eq("user_id", user_id)\
        .eq("producto_id", prod_id)\
        .execute()
        
    if not inv.data:
        return prod_id, prod_nombre, 0, 0 
    
    item = inv.data[0]
    return prod_id, prod_nombre, item["precio_venta"], item["stock_actual"]

# --- HERRAMIENTAS (TOOLS) ---

def tool_consultar_inventario(producto_nombre: str, user_id: str):
    pid, nombre, precio, stock = buscar_producto_id(producto_nombre, user_id)
    
    # 1. VERIFICACIÓN DE AMBIGÜEDAD (AGREGADO)
    if not pid:
        if nombre and "Encontré varios" in nombre:
            return nombre # Devolvemos la pregunta a la IA
        return f"No encontré nada parecido a '{producto_nombre}' en el catálogo."
        
    if stock == 0 and precio == 0:
        return f"El producto '{nombre}' existe en el catálogo global, pero TÚ no lo tienes en tu inventario."
    
    return f"📦 {nombre}: Tienes {stock} unidades. Precio venta: ${precio}."

def tool_registrar_venta(producto_nombre: str, cantidad: int, precio_venta_real: int, metodo_pago: str, user_id: str):
    pid, nombre, precio_db, stock = buscar_producto_id(producto_nombre, user_id)
    
    print(f"🛒 VENTA | producto='{producto_nombre}' → pid={pid}, nombre={nombre}, precio_db={precio_db}, stock={stock}")

    if not pid:
        if nombre and "Encontré varios" in nombre: return nombre 
        return f"❌ Error: No encuentro '{producto_nombre}'."
    
    if stock < cantidad:
        return f"⚠️ Stock insuficiente. Tienes {stock}, necesitas {cantidad}."
    
    if precio_venta_real == 0 and precio_db == 0:
        return "🛑 ERROR: Falta el precio. Pregunta al usuario y vuelve a ejecutar esta función."
    if metodo_pago == "preguntar":
        return "🛑 ERROR: Falta el método de pago. Pregunta al usuario (Efectivo/Tarjeta) y vuelve a ejecutar esta función."
    
    precio_final = precio_venta_real if precio_venta_real > 0 else precio_db
    nuevo_stock = stock - cantidad

    # Actualización ATÓMICA con logging completo
    try:
        inv_row = supabase.table("inventario_local")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("producto_id", pid)\
            .single()\
            .execute()

        print(f"🔍 Fila inventario encontrada: {inv_row.data}")

        if inv_row.data:
            row_id = inv_row.data["id"]
            update_result = supabase.table("inventario_local")\
                .update({"stock_actual": nuevo_stock})\
                .eq("id", row_id)\
                .execute()
            print(f"✅ Stock actualizado → nuevo_stock={nuevo_stock} | resultado={update_result.data}")
        else:
            print(f"❌ NO SE ENCONTRÓ fila para user_id={user_id}, producto_id={pid}")
            return f"❌ Error interno: producto encontrado en catálogo pero no en tu inventario local."

    except Exception as e:
        print(f"💥 ERROR al actualizar inventario: {e}")
        return f"❌ Error al actualizar stock: {str(e)}"

    # Registro en tabla "ventas"
    try:
        venta_data = {
            "user_id": user_id,
            "total": precio_final * cantidad,
            "metodo_pago": metodo_pago,
            "detalles": [{"producto": nombre, "cantidad": cantidad, "precio": precio_final}],
            "created_at": datetime.now().isoformat()
        }
        venta_result = supabase.table("ventas").insert(venta_data).execute()
        print(f"✅ Venta guardada en BD | id={venta_result.data[0]['id'] if venta_result.data else 'sin id'}")
    except Exception as e:
        print(f"💥 ERROR al guardar venta: {e}")
        return f"❌ Stock actualizado pero error al guardar la venta: {str(e)}"

    return f"✅ Venta exitosa: {cantidad}x {nombre}. Total: ${precio_final * cantidad}. Stock restante: {nuevo_stock}."

def tool_actualizar_precio(producto_nombre: str, nuevo_precio: int, user_id: str):
    pid, nombre, precio, stock = buscar_producto_id(producto_nombre, user_id)
    
    if not pid:
        if nombre and "Encontré varios" in nombre:
            return nombre 
        return "No encontrado."
    
    supabase.table("inventario_local")\
        .update({"precio_venta": nuevo_precio})\
        .eq("user_id", user_id)\
        .eq("producto_id", pid)\
        .execute()
    return f"🏷️ Precio actualizado: {nombre} ahora cuesta ${nuevo_precio}."

def tool_actualizar_stock(producto_nombre: str, cantidad_a_sumar: int, user_id: str):
    pid, nombre, precio, stock = buscar_producto_id(producto_nombre, user_id)
    
    if not pid:
        if nombre and "Encontré varios" in nombre:
            return nombre 
        return f"No encuentro '{producto_nombre}'. Para crear productos nuevos usa el panel administrativo."
        
    nuevo_stock = stock + cantidad_a_sumar
    
    check = supabase.table("inventario_local").select("id").eq("user_id", user_id).eq("producto_id", pid).execute()
    
    if check.data:
        supabase.table("inventario_local").update({"stock_actual": nuevo_stock}).eq("id", check.data[0]["id"]).execute()
    else:
        supabase.table("inventario_local").insert({
            "user_id": user_id, 
            "producto_id": pid, 
            "stock_actual": nuevo_stock,
            "precio_venta": 0
        }).execute()
        
    return f"🚛 Carga recibida: Agregadas {cantidad_a_sumar} unidades de {nombre}. Nuevo stock: {nuevo_stock}."

def tool_ver_resumen_ventas(periodo: str, user_id: str):
    """
    Muestra el total vendido hoy (o en el periodo solicitado).
    """
    # Por simplicidad del MVP, asumiremos "hoy"
    # Postgres tiene funciones de fecha, pero para no complicarnos con Timezones
    # vamos a pedir las ventas de las últimas 24 hrs o simplemente traer las últimas 50 y filtrar en python.
    
    # Opción PRO: Usar filtro de fecha en Supabase (gte = Greater Than or Equal to Today)
    from datetime import datetime, timezone
    
    # Fecha de hoy en formato YYYY-MM-DD
    hoy = datetime.now().strftime("%Y-%m-%d")
    
    # Traemos ventas creadas hoy
    response = supabase.table("ventas")\
        .select("total, detalles, created_at")\
        .eq("user_id", user_id)\
        .gte("created_at", f"{hoy}T00:00:00")\
        .execute()
        
    if not response.data:
        return f"📅 Resumen ({hoy}): No has registrado ventas hoy. ¡Ánimo!"
    
    ventas = response.data
    total_dia = sum([v["total"] for v in ventas])
    cantidad_ventas = len(ventas)
    
    # Resumen de productos vendidos
    resumen_prods = {}
    for v in ventas:
        detalles = v["detalles"] # Es una lista de dicts
        for d in detalles:
            prod = d["producto"]
            cant = d["cantidad"]
            resumen_prods[prod] = resumen_prods.get(prod, 0) + cant
            
    texto_prods = ", ".join([f"{k} ({v})" for k,v in resumen_prods.items()])
    
    return f"💰 **CIERRE DE CAJA ({hoy})**:\n- Total Vendido: ${total_dia:,}\n- N° Transacciones: {cantidad_ventas}\n- Lo que más salió: {texto_prods}"

def tool_crear_producto(nombre_nuevo: str, categoria: str, user_id: str):
    """
    Crea un producto nuevo en el catálogo global si no existe.
    """
    nombre_limpio = nombre_nuevo.strip().title() # Ej: "Doritos Queso L"
    
    # 1. Verificamos que no exista (para evitar duplicados por error)
    existe = supabase.table("catalogo_universal")\
        .select("id")\
        .ilike("nombre", nombre_limpio)\
        .execute()
        
    if existe.data:
        return f"⚠️ El producto '{nombre_limpio}' ya existe en el catálogo. No es necesario crearlo."

    # 2. Insertamos en el Catálogo Universal
    # Nota: 'sinonimos' queda vacío por defecto
    nuevo_prod = supabase.table("catalogo_universal").insert({
        "nombre": nombre_limpio,
        "categoria": categoria
    }).execute()
    
    if not nuevo_prod.data:
        return "❌ Error al crear el producto en la base de datos."
        
    # 3. Retornamos éxito
    return f"✅ Producto creado exitosamente: '{nombre_limpio}' (Categoría: {categoria}). Ahora puedes agregar stock o venderlo."

def tool_inicializar_inventario(user_id: str):
    # ... (Tu función mejorada de la respuesta anterior) ...
    existing = supabase.table("inventario_local").select("producto_id").eq("user_id", user_id).execute()
    mis_ids_existentes = {item["producto_id"] for item in existing.data} 

    catalog = supabase.table("catalogo_universal").select("id, nombre").execute()
    if not catalog.data: return "❌ Error: Catálogo vacío."

    items_a_insertar = []
    nombres_nuevos = []
    for prod in catalog.data:
        if prod["id"] not in mis_ids_existentes:
            items_a_insertar.append({
                "user_id": user_id, "producto_id": prod["id"],
                "stock_actual": 0, "stock_minimo": 5, "precio_venta": 0
            })
            nombres_nuevos.append(prod["nombre"])

    if not items_a_insertar: return "✅ Tu inventario ya está completo."

    try:
        supabase.table("inventario_local").insert(items_a_insertar).execute()
        ejemplos = ", ".join(nombres_nuevos[:3])
        return f"✅ Agregué {len(items_a_insertar)} productos nuevos (como {ejemplos})."
    except Exception as e: return f"❌ Error DB: {str(e)}"

    # 4. Insertamos en Supabase
    try:
        resultado = supabase.table("inventario_local").insert(items_a_insertar).execute()
        cantidad = len(resultado.data) if resultado.data else len(items_a_insertar)
        return f"✅ ¡Listo! He cargado {cantidad} productos base a tu inventario. Ahora puedes decirme 'Llegaron 10 cocas' para empezar a sumar stock."
    except Exception as e:
        return f"❌ Error al guardar en base de datos: {str(e)}"

@router.get("/stats", status_code=status.HTTP_200_OK)
def get_dashboard_stats(user = Depends(get_current_user)):
    try:
        hoy = date.today().isoformat()
        print(f"📊 Cargando stats para user {user.id}, fecha: {hoy}")

        # --- FIX: Verificamos que la tabla "ventas" existe antes de consultar ---
        try:
            ventas_hoy = supabase.table("ventas")\
                .select("total, detalles")\
                .eq("user_id", user.id)\
                .gte("created_at", f"{hoy}T00:00:00")\
                .execute()
            print(f"✅ Ventas encontradas: {len(ventas_hoy.data) if ventas_hoy.data else 0}")
        except Exception as db_err:
            # Error específico de base de datos — lo mostramos claro en los logs
            print(f"❌ ERROR AL CONSULTAR TABLA 'ventas': {db_err}")
            print("👉 Verifica en Supabase que la tabla se llame exactamente 'ventas' (con s)")
            # Devolvemos stats vacías para que el frontend no colapse
            return {
                "ventas_hoy": 0,
                "productos_vendidos": 0,
                "alertas_stock": 0,
                "chart_labels": [],
                "chart_data": [],
                "error_detalle": f"Error de base de datos: {str(db_err)}"
            }
            
        total_dinero = 0
        total_productos = 0
        prod_contador = {}
        
        if ventas_hoy.data:
            for v in ventas_hoy.data:
                total_dinero += v.get("total", 0)
                for d in v.get("detalles", []):
                    total_productos += d.get("cantidad", 0)
                    nombre = d.get("producto", "Desconocido")
                    prod_contador[nombre] = prod_contador.get(nombre, 0) + d.get("cantidad", 0)

        top_5 = sorted(prod_contador.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Alertas de stock
        alertas = supabase.table("inventario_local").select("id").eq("user_id", user.id).lt("stock_actual", 5).execute()
        
        return {
            "ventas_hoy": total_dinero,
            "productos_vendidos": total_productos,
            "alertas_stock": len(alertas.data) if alertas.data else 0,
            "chart_labels": [item[0] for item in top_5],
            "chart_data": [item[1] for item in top_5]
        }
    except Exception as e:
        print(f"❌ Error general en /stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- SCHEMA PARA OPENAI ---
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "consultar_inventario",
            "description": "Consulta stock y precio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "producto_nombre": {"type": "string"}
                },
                "required": ["producto_nombre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "actualizar_precio",
            "description": "Cambia el precio oficial de un producto en la estantería.",
            "parameters": {
                "type": "object",
                "properties": {
                    "producto_nombre": {"type": "string"},
                    "nuevo_precio": {"type": "integer"}
                },
                "required": ["producto_nombre", "nuevo_precio"]
            }
        }
    },
{
        "type": "function",
        "function": {
            "name": "registrar_venta",
            "description": (
                "Registra una venta y descuenta el stock. "
                "REGLA CRITICA: SIEMPRE ejecuta esta funcion antes de responder al usuario. "
                "NUNCA redactes el mensaje de exito sin haber llamado a esta funcion primero — "
                "el resultado que ella devuelva es lo que debes comunicar. "
                "Si el metodo de pago no fue mencionado, pasa 'preguntar' y la funcion te "
                "indicara que debes pedirlo; luego llamala de nuevo con todos los datos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "producto_nombre": {"type": "string"},
                    "cantidad": {"type": "integer"},
                    "precio_venta_real": {"type": "integer", "description": "Precio unitario real. 0 si no se menciona explicitamente."},
                    "metodo_pago": {
                        "type": "string",
                        "enum": ["efectivo", "tarjeta", "transferencia", "preguntar"],
                        "description": "El medio de pago. Si el usuario NO lo menciono explicitamente, USA 'preguntar'. Nunca asumas ni inventes el metodo."
                    }
                },
                "required": ["producto_nombre", "cantidad", "precio_venta_real", "metodo_pago"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "actualizar_stock",
            "description": "Suma stock (llegadas/compras).",
            "parameters": {
                "type": "object",
                "properties": {
                    "producto_nombre": {"type": "string"},
                    "cantidad_a_sumar": {"type": "integer"}
                },
                "required": ["producto_nombre", "cantidad_a_sumar"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ver_mis_productos",
            "description": "Muestra una lista completa de todos los productos que el usuario tiene en su inventario local.",
            "parameters": {
                "type": "object",
                "properties": {}, # No requiere parámetros
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ver_resumen_ventas",
            "description": "Muestra el total de dinero ganado hoy y qué productos se vendieron.",
            "parameters": {
                "type": "object",
                "properties": {"periodo": {"type": "string", "description": "El periodo a consultar (ej: 'hoy')."}
                },
                "required": ["periodo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "crear_producto",
            "description": "Crea un producto totalmente nuevo en el catálogo global. Úsalo cuando 'actualizar_stock' falle porque el producto no existe.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_nuevo": {"type": "string", "description": "El nombre oficial del producto (Ej: Doritos Queso L)."},
                    "categoria": {
                        "type": "string", 
                        "description": "La categoría estimada (Ej: Snacks, Bebidas, Abarrotes, Limpieza).",
                        "enum": ["Abarrotes", "Snacks", "Bebidas", "Lácteos", "Limpieza", "Panadería", "Otros"]
                    }
                },
                "required": ["nombre_nuevo", "categoria"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inicializar_inventario",
            "description": "Carga masiva de productos básicos. Úsalo SOLO cuando el usuario diga que no tiene productos, que está vacío o pida 'agregar algunos productos' al inicio.",
            "parameters": {
                "type": "object",
                "properties": {}, 
                "required": []
            }
        }
    }
]

PALABRAS_VENTA = ["vend", "salió", "salieron", "despach", "cobr", "vendí", "vendido", "se llevaron", "vendimos"]
PALABRAS_STOCK = ["llegaron", "llegó", "compré", "compramos", "recibí", "recibimos", "entró", "entraron", "cargué"]
PALABRAS_EXCLUSION = ["robaron", "robó", "caducar", "caducaron", "vencieron", "vencido", "dañaron", "perdieron", "rompieron", "quebraron"]

def detectar_herramienta_forzada(mensaje: str):
    msg = mensaje.lower()
    if any(p in msg for p in PALABRAS_EXCLUSION):
        return "auto"
    if any(p in msg for p in PALABRAS_VENTA):
        return {"type": "function", "function": {"name": "registrar_venta"}}
    if any(p in msg for p in PALABRAS_STOCK):
        return {"type": "function", "function": {"name": "actualizar_stock"}}
    return "auto"
#MODELO
class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
def chat_with_tools(request: ChatRequest, user = Depends(confirmar_pago_activo)):
    current_user_id = user.id

    try:
        # 1. Datos del Negocio
        data_perfil = supabase.table("profiles").select("nombre_negocio").eq("id", current_user_id).execute()
        nombre_negocio = data_perfil.data[0]["nombre_negocio"] if data_perfil.data else "Tu Negocio"

        # 2. Prompt del Sistema
        raw_prompt = load_system_prompt()
        system_instruction = raw_prompt.replace("{nombre_negocio}", nombre_negocio)

        # 3. 🧠 MEMORIA
        history_messages = get_chat_history(current_user_id)
        messages = [{"role": "system", "content": system_instruction}]
        for msg in history_messages:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": request.message})

        # 4. Detectar si debemos forzar una herramienta en la primera llamada
        primera_tool_choice = detectar_herramienta_forzada(request.message)
        print(f"🎯 tool_choice detectado: {primera_tool_choice}")

        # 5. Bucle del Agente
        final_reply = ""
        es_primera_llamada = True

        for _ in range(5):
            tool_choice_actual = primera_tool_choice if es_primera_llamada else "auto"
            es_primera_llamada = False

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools_schema,
                tool_choice=tool_choice_actual
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            # Si la IA responde texto final (sin llamar herramientas)
            if not tool_calls:
                final_reply = response_message.content
                break

            # Si llama herramientas, guardamos esa intención temporalmente en 'messages'
            messages.append(response_message) 

            for tool_call in tool_calls:
                fname = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                print(f"🤖 Ejecutando: {fname} | Args: {args}")
                
                result_content = "Error"
                
                # Ejecutamos la función correspondiente
                if fname == "consultar_inventario": result_content = tool_consultar_inventario(args["producto_nombre"], current_user_id)
                elif fname == "registrar_venta": result_content = tool_registrar_venta(args["producto_nombre"], args["cantidad"], args.get("precio_venta_real",0), args.get("metodo_pago","preguntar"), current_user_id)
                elif fname == "actualizar_stock": result_content = tool_actualizar_stock(args["producto_nombre"], args["cantidad_a_sumar"], current_user_id)
                elif fname == "actualizar_precio": result_content = tool_actualizar_precio(args["producto_nombre"], args["nuevo_precio"], current_user_id)
                elif fname == "ver_mis_productos": result_content = tool_ver_mis_productos(current_user_id)
                elif fname == "ver_resumen_ventas": result_content = tool_ver_resumen_ventas(args.get("periodo", "hoy"), current_user_id)
                elif fname == "crear_producto": result_content = tool_crear_producto(args["nombre_nuevo"], args["categoria"], current_user_id)
                elif fname == "inicializar_inventario": result_content = tool_inicializar_inventario(current_user_id)

                # Le devolvemos el resultado a la IA
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": fname,
                    "content": str(result_content),
                })
        
        # 5. 💾 GUARDAR EN MEMORIA (Largo Plazo)
        # Solo guardamos el mensaje del usuario y la respuesta final de la IA
        save_chat_message(current_user_id, "user", request.message)
        save_chat_message(current_user_id, "assistant", final_reply)

        return {"reply": final_reply}

    except Exception as e:
        print(f"Error chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Recibe un audio (blob), lo guarda temporalmente, lo envía a Whisper
    y devuelve el texto transcrito.
    """
    try:
        # 1. Guardar el archivo temporalmente en el servidor
        # Whisper necesita leer un archivo real del disco
        temp_filename = f"temp_{file.filename}.webm"
        
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Enviarlo a OpenAI Whisper
        print("🎤 Procesando audio con Whisper...")
        with open(temp_filename, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                language="es" # Forzamos español para mejorar precisión
            )
            
        # 3. Limpieza: Borrar el archivo temporal
        os.remove(temp_filename)
        
        texto_transcrito = transcript.text
        print(f"🗣️ Texto detectado: {texto_transcrito}")
        
        return {"text": texto_transcrito}

    except Exception as e:
        print(f"Error en transcripción: {e}")
        raise HTTPException(status_code=500, detail=str(e))