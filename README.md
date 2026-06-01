# 📦 Stockeadito - Sistema Inteligente de Ventas

Stockeadito es una solución avanzada de gestión de inventario y ventas impulsada por Inteligencia Artificial, diseñada para negocios locales. Permite registrar ventas, gestionar stock y obtener métricas en tiempo real mediante un asistente conversacional natural.

---

## 🌟 Accesibilidad e Inclusión Digital

Nuestro sistema está diseñado para ser universal. Entendemos que no todos los usuarios tienen la misma facilidad con la escritura o los interfaces complejos. Por ello:

- **Interfaz de Voz:** Permite realizar todas las operaciones (registrar ventas, consultar stock, actualizar precios) mediante mensajes de audio.
- **Baja barrera de entrada:** Ideal para personas con baja alfabetización digital o que prefieren una comunicación oral directa, eliminando la necesidad de navegar por menús complicados o escribir largos formularios.
- **Intuitivo:** La IA entiende el lenguaje cotidiano, facilitando la adopción tecnológica para cualquier comerciante.

---

## 🚀 Características Principales

- **IA Cognitiva:** Asistente capaz de entender lenguaje natural (escrito y hablado).
- **Integración en Tiempo Real:** Backend robusto con FastAPI y base de datos en Supabase.
- **Gestión Inteligente:** Descuento automático de stock y validación de precios.
- **Dashboard Visual:** Panel de control con métricas del día y gráficos dinámicos del Top de productos más vendidos.
- **Transcripción IA:** Integración con Whisper AI para convertir audios en órdenes de gestión precisa.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Base de Datos | Supabase (PostgreSQL + Auth + RLS) |
| IA | OpenAI GPT-4o-mini (Function Calling), Whisper |
| Frontend | JavaScript vanilla, Chart.js, Web Audio API |
| Auth | JWT via Supabase Auth |

---

## ⚙️ Estructura del Proyecto

```
/
├── main.py                        # Punto de entrada, rutas y middlewares
├── database.py                    # Conexión con Supabase
├── dependencies.py                # Lógica de autenticación JWT
├── requirements.txt
├── prompts/
│   └── stockeadito_system.md      # Instrucciones base de la IA
├── routers/
│   ├── auth.py                    # Login y registro
│   ├── chat.py                    # Corazón del sistema (IA, Tools, Métricas)
│   ├── inventory.py               # CRUD de inventario
│   ├── sales.py                   # Endpoints de ventas manuales
│   └── pagos.py                   # Gestión de suscripciones
└── frontend/
    ├── index.html                 # Login
    ├── dashboard.html             # Panel principal
    └── assets/
        ├── css/style.css
        └── js/
            ├── app.js             # Lógica del dashboard
            ├── auth.js            # Manejo de sesión
            └── pagos.js
```

---

## 🔧 Instalación y Configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/stockeadito-mvp.git
cd stockeadito-mvp
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copia `.env.example` a `.env` y rellena los valores:

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJ...
```

### 4. Configurar Supabase

Crea las siguientes tablas en tu proyecto de Supabase:

- `profiles` — datos del negocio por usuario
- `catalogo_universal` — catálogo global de productos
- `inventario_local` — stock por usuario
- `ventas` — registro de transacciones
- `chat_history` — memoria del asistente

### 5. Ejecutar el servidor

```bash
uvicorn main:app --reload
```

Abre `http://localhost:8000` en tu navegador.

---

## 💡 Cómo funciona la IA

El sistema utiliza **Function Calling** de OpenAI para interactuar con la base de datos de forma segura y controlada.

1. **Análisis:** La IA interpreta la orden (sea texto o voz).
2. **Detección:** El backend identifica la intención (venta, consulta, actualización) y fuerza la herramienta correcta.
3. **Validación:** Comprueba stock disponible antes de ejecutar cualquier cambio.
4. **Ejecución:** Actualiza el inventario en Supabase y registra la venta con fecha, método de pago y detalles.
5. **Respuesta:** Confirma la acción al usuario de forma clara y en lenguaje chileno natural.

---

## 📝 Comandos Comunes

```
"Vendí 2 Sprite 1.5L, pagaron con efectivo"
"¿Cómo va mi venta de hoy?"
"Agrega 10 unidades de Arroz"
"¿Qué es lo que más se ha vendido?"
```

> También puedes enviar un audio diciendo cualquiera de estos comandos y el sistema lo transcribirá automáticamente con Whisper.

---

## 📄 Licencia

MIT

---

Desarrollado para la optimización de procesos de inventario local, democratizando el acceso a la tecnología. 🚀