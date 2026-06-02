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
<img width="1899" height="916" alt="Screenshot 2026-06-01 205136" src="https://github.com/user-attachments/assets/dd793b3e-ab1e-41ce-a4f2-fc4e110187ec" />
<img width="1916" height="920" alt="Screenshot 2026-06-01 205506" src="https://github.com/user-attachments/assets/74dadb66-9e5d-4d02-b527-6e66f71af28c" />
<img width="1916" height="915" alt="Screenshot 2026-06-01 205429" src="https://github.com/user-attachments/assets/62664dc4-a3ce-415d-86bd-5cc5f70f2222" />
<img width="502" height="384" alt="Screenshot 2026-06-01 205359" src="https://github.com/user-attachments/assets/84a5e5e6-5ab2-4eb5-9073-76da81c59ee0" />
<img width="1916" height="919" alt="Screenshot 2026-06-01 205351" src="https://github.com/user-attachments/assets/2800dacd-23db-4922-9257-98a8446787cd" />
<img width="1848" height="668" alt="Screenshot 2026-06-01 205339" src="https://github.com/user-attachments/assets/7c8aa620-d725-448c-93d1-edbf743a0466" />
<img width="1905" height="919" alt="Screenshot 2026-06-01 205245" src="https://github.com/user-attachments/assets/67ce0ed7-914d-4f22-9981-ac69977ece50" />
<img width="1906" height="913" alt="Screenshot 2026-06-01 205240" src="https://github.com/user-attachments/assets/2da9d706-0db2-4050-9139-55d4662e2c2a" />
<img width="1905" height="914" alt="Screenshot 2026-06-01 205224" src="https://github.com/user-attachments/assets/d2efd873-2194-4f45-a77c-4d617334fdd0" />
<img width="1899" height="916" alt="Screenshot 2026-06-01 205218" src="https://github.com/user-attachments/assets/915b69e8-16b3-457c-a409-caf4efdb9d52" />
<img width="1905" height="915" alt="Screenshot 2026-06-01 205147" src="https://github.com/user-attachments/assets/0620009e-0c15-4a44-9b3f-59f73267c9d6" />
<img width="1911" height="906" alt="Screenshot 2026-06-01 204753" src="https://github.com/user-attachments/assets/4e8b2c85-0aef-4b89-90a9-eece6b829585" />
<img width="1899" height="913" alt="Screenshot 2026-06-01 204736" src="https://github.com/user-attachments/assets/69f4c66d-f7e5-4b92-a84d-685ba4458fb1" />
<img width="1885" height="897" alt="Screenshot 2026-06-01 204717" src="https://github.com/user-attachments/assets/da0ce45c-ac03-4c4a-9794-dc6a8d73d0ee" />
<img width="1915" height="911" alt="Screenshot 2026-06-01 205639" src="https://github.com/user-attachments/assets/aa4596d9-df11-4a7c-aa1e-c8391f6d69dc" />
<img width="1913" height="917" alt="Screenshot 2026-06-01 205633" src="https://github.com/user-attachments/assets/29c2a294-5f91-42d2-a887-d4f7e937432e" />
<img width="1919" height="911" alt="Screenshot 2026-06-01 205523" src="https://github.com/user-attachments/assets/f4b18d82-64f6-4e5e-a635-ce56060b3f46" />
