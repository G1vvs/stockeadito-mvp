import json
import os
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from openai import OpenAI
from dependencies import get_current_user
from database import supabase
from datetime import datetime
#iniciamos el cliente openai
client = OpenAI()

router = APIRouter(
    tags=["AI Brain"]
)
# Cargar el prompt
def load_system_prompt():
    """
    Lee el archivo markdown desde la carpeta 'prompts'
    """
    try:
        # 1. Obtener la ruta base del proyecto (donde está main.py)
        # __file__ es este archivo (routers/chat.py).
        # Vamos dos niveles arriba: routers/.. -> stockeadito-mvp/
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 2. Construir la ruta al archivo md
        file_path = os.path.join(base_dir, "prompts", "stockeadito_system.md")
        
        # 3. Abrir y leer (encoding utf-8 es CRÍTICO para tildes y emojis)
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
            
    except Exception as e:
        print(f"Error leyendo el prompt: {e}")
        # Retornamos un prompt básico de respaldo por si falla el archivo
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
    Búsqueda inteligente V4: Soporte para Sinónimos/Alias (Marraqueta = Batido)
    """
    termino = nombre_vago.strip().lower()
    print(f"🔎 Buscando término original: '{termino}'")

    # --- 1. SUB-FUNCIÓN: SINGULARIZADOR ---
    def singularizar(palabra):
        if palabra.endswith("es"): return palabra[:-2]
        if palabra.endswith("s"): return palabra[:-1]
        return palabra

    # --- 2. SUB-FUNCIÓN: PROCESAR RESULTADOS ---
    def procesar_resultados(data):
        if not data: return None
        nombres_encontrados = [p['nombre'] for p in data]
        print(f"   👀 Coincidencias encontradas: {nombres_encontrados}")

        if len(data) > 1:
            lista_str = ", ".join(nombres_encontrados)
            return None, f"❌ Encontré varios productos: {lista_str}. ¿Cuál de estos es?", 0, 0
        
        return data[0]["id"], data[0]["nombre"], 0, 0

    # --- LÓGICA DE BÚSQUEDA HÍBRIDA (NOMBRE O SINÓNIMOS) ---
    def ejecutar_busqueda(termino_busqueda):
        # Preparamos el término para SQL (ej: %pan batido%)
        t = f"%{termino_busqueda}%"
        
        # EL TRUCO ESTÁ AQUÍ 👇
        # Le decimos: Busca donde nombre sea parecido A t ... O ... sinonimos sea parecido A t
        filtro_or = f"nombre.ilike.{t},sinonimos.ilike.{t}"
        
        return supabase.table("catalogo_universal")\
            .select("id, nombre")\
            .or_(filtro_or)\
            .limit(5)\
            .execute()

    # INTENTO 1: Búsqueda Exacta/Flexible
    # Quitamos espacios para hacer match parcial (opcional, pero ayuda)
    termino_limpio = termino.replace(" ", "%")
    response = ejecutar_busqueda(termino_limpio)
    
    if response.data:
        resultado = procesar_resultados(response.data)
        if resultado[0] is None: return resultado
        prod_id, prod_nombre, _, _ = resultado
    
    else:
        # INTENTO 2: Plan B (Raíz Singularizada)
        palabras = termino.split(" ")
        primera_palabra = palabras[0]
        raiz = singularizar(primera_palabra) 
        
        print(f"🔄 Intento 2: Buscando raíz '{raiz}'")
        
        if len(raiz) >= 3:
            response = ejecutar_busqueda(raiz)
            
            resultado_b = procesar_resultados(response.data)
            if not resultado_b: return None, None, 0, 0
            if resultado_b[0] is None: return resultado_b
            
            prod_id, prod_nombre, _, _ = resultado_b
        else:
            return None, None, 0, 0

    # 3. Búsqueda en Inventario Local
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
    
    # 1. VERIFICACIÓN DE AMBIGÜEDAD
    if not pid:
        if nombre and "Encontré varios" in nombre:
            return nombre 
        return f"❌ Error: No encuentro el producto '{producto_nombre}'."
    
    # 2. VERIFICACIÓN DE STOCK
    if stock < cantidad:
        return f"⚠️ Stock insuficiente de {nombre}. Tienes {stock}, intentas vender {cantidad}."
    
    # 3. 🛡️ BLOQUEO DE SEGURIDAD DE PRECIO (NUEVO)
    # Si la IA no detectó precio en el mensaje (0) Y en la base de datos tampoco hay (0)
    if precio_venta_real == 0 and precio_db == 0:
        return f"🛑 ¡Espera! El producto '{nombre}' no tiene precio registrado y no me dijiste a cuánto lo vendiste. ¿Cuál es el precio para poder registrarlo?"
    
    # 4. 🛡️ BLOQUEO DE MÉTODO DE PAGO (NUEVO) 💳
    if metodo_pago == "preguntar":
        return f"💳 Falta el medio de pago. ¿La venta de {nombre} fue con Efectivo, Tarjeta o Transferencia?"
    # LÓGICA DE PRECIO INTELIGENTE
    precio_final = precio_db
    msg_precio = ""

    if precio_venta_real > 0:
        precio_final = precio_venta_real
        if precio_db == 0:
            supabase.table("inventario_local")\
                .update({"precio_venta": precio_venta_real})\
                .eq("user_id", user_id)\
                .eq("producto_id", pid)\
                .execute()
            msg_precio = "(He guardado este precio como el oficial para el futuro)."
    
    total = precio_final * cantidad
    nuevo_stock = stock - cantidad
    
    supabase.table("inventario_local")\
        .update({"stock_actual": nuevo_stock})\
        .eq("user_id", user_id)\
        .eq("producto_id", pid)\
        .execute()
        
    venta_data = {
        "user_id": user_id,
        "total": total,
        "metodo_pago": "efectivo",
        "detalles": [{"producto": nombre, "cantidad": cantidad, "precio": precio_final}]
    }
    supabase.table("ventas").insert(venta_data).execute()
    
    return f"✅ Venta exitosa: {cantidad}x {nombre} a ${precio_final} c/u. Total: ${total}. Te quedan {nuevo_stock}. {msg_precio}"

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
            "description": "Registra una venta. Requiere nombre, cantidad, precio y método de pago.",
            "parameters": {
                "type": "object",
                "properties": {
                    "producto_nombre": {"type": "string"},
                    "cantidad": {"type": "integer"},
                    "precio_venta_real": {"type": "integer", "description": "Precio unitario real. 0 si no se menciona."},
                    "metodo_pago": {
                        "type": "string",
                        "enum": ["efectivo", "tarjeta", "transferencia", "preguntar"],
                        "description": "El medio de pago. Si el usuario NO lo menciona, DEBES seleccionar 'preguntar'."
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
    }
]

#MODELO
class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
def chat_with_tools(request: ChatRequest, user = Depends(get_current_user)):
    current_user_id = user.id

    try:
        # 1. Buscar el nombre del negocio (Igual que antes)
        data_perfil = supabase.table("profiles")\
            .select("nombre_negocio")\
            .eq("id", current_user_id)\
            .execute()
            
        nombre_negocio = "Tu Negocio"
        if data_perfil.data:
            nombre_negocio = data_perfil.data[0]["nombre_negocio"]

        # 2. Cargar el prompt base desde el archivo
        raw_prompt = load_system_prompt()
        
        # 3. 👇 AQUÍ ESTÁ LA MAGIA: Rellenamos la plantilla
        # Python busca "{nombre_negocio}" en el texto y lo cambia por "Supermercado Giovanni"
        system_instruction = raw_prompt.replace("{nombre_negocio}", nombre_negocio)

        # 4. Creamos los mensajes
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": request.message}
        ]

        # --- BUCLE AGENTE (AGENT LOOP) 🔄 ---
        # Permitimos hasta 5 vueltas de pensamiento para que la IA pueda corregirse
        # (Ej: Crear producto -> Luego agregar stock -> Luego confirmar)
        for _ in range(5): 
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools_schema,
                tool_choice="auto"
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            # CASO 1: La IA quiere hablar (no usar herramientas)
            if not tool_calls:
                return {"reply": response_message.content}

            # CASO 2: La IA quiere usar herramientas
            # Agregamos la intención de la IA al historial para mantener el contexto
            messages.append(response_message) 

            for tool_call in tool_calls:
                fname = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                print(f"🤖 Ejecutando: {fname} | Args: {args}")
                
                result_content = "Error desconocido"
                
                # --- MAPEO DE TODAS LAS HERRAMIENTAS ---
                if fname == "consultar_inventario":
                    result_content = tool_consultar_inventario(args["producto_nombre"], current_user_id)
                    
                elif fname == "registrar_venta":
                    result_content = tool_registrar_venta(
                        args["producto_nombre"], 
                        args["cantidad"], 
                        args.get("precio_venta_real", 0),
                        args.get("metodo_pago", "preguntar"), 
                        current_user_id
                    )
                    
                elif fname == "actualizar_stock":
                    result_content = tool_actualizar_stock(args["producto_nombre"], args["cantidad_a_sumar"], current_user_id)
                    
                elif fname == "actualizar_precio":
                    result_content = tool_actualizar_precio(args["producto_nombre"], args["nuevo_precio"], current_user_id)
                    
                elif fname == "ver_mis_productos":
                    result_content = tool_ver_mis_productos(current_user_id)
                    
                elif fname == "ver_resumen_ventas":
                    result_content = tool_ver_resumen_ventas(args.get("periodo", "hoy"), current_user_id)
                    
                elif fname == "crear_producto":
                    result_content = tool_crear_producto(args["nombre_nuevo"], args["categoria"], current_user_id)

                # Agregamos el resultado de la herramienta al historial
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": fname,
                    "content": str(result_content),
                })
            
            # --- FIN DEL CICLO FOR ---
            # El código vuelve arriba, envía 'messages' (con los resultados nuevos) a la IA
            # y la IA decide qué hacer a continuación.

        # Si pasaron 5 vueltas y no terminó, cortamos por seguridad
        return {"reply": "La IA pensó demasiado y se detuvo por seguridad."}

    except Exception as e:
        print(f"Error chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/test")
def test_ai_connection(request: ChatRequest):
    '''
    Envia un mensaje simple a chatgpt-4o-mini para verificar
    '''
    try:
        print(f"Enviado a OpenAI: {request.message}")
        completion = client.chat.completions.create(
            model = "gpt-4o-mini", # usamos el modelo barato
            messages=[
                {"role": "system", "content": "Eres un asistente útil de un minimarket chileno."},
                {"role": "user", "content": request.message}
            ]
        )
        response_text = completion.choices[0].message.content
        return {"reply": response_text}
    
    except Exception as e:
        print(f"Error OpenAI: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=str(e))