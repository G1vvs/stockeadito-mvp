# STOCKBADITO - AGENTS.MD

## 1. MISIÓN DEL PROYECTO
Stockeadito es una aplicación Web Progresiva (PWA) SaaS diseñada para dueños de minimarkets y almacenes de barrio. Su objetivo es democratizar la gestión de inventario y ventas mediante Inteligencia Artificial (Audio a Texto).
El flujo principal consiste en que el usuario dicta sus ventas ("Vendí 2 leches y un pan") y la IA actualiza el inventario y genera métricas automáticamente, sin necesidad de digitar códigos ni usar lectores de barra.

## 2. STACK TECNOLÓGICO (The Rules)
La IA debe generar código respetando estrictamente estas tecnologías:

- **Backend:** Python 3.12 + FastAPI.
- **Base de Datos:** PostgreSQL vía Supabase.
- **Frontend:** HTML5, CSS y JavaScript (Vanilla). Sin frameworks complejos (React/Vue/Angular) para mantener la ligereza de la PWA.
- **IA:** OpenAI API (Whisper para transcripción de audio + GPT-4o-mini para lógica de negocio).
- **Despliegue:** Render/Railway (Backend) y GitHub Pages/Netlify (Frontend).

## 3. REGLAS DE CODIFICACIÓN Y ESTILO

### General
- **Idioma:** Todo el código, comentarios y documentación deben estar en Español.
- **Comentarios:** Cada función nueva debe incluir un bloque de comentario explicativo (Docstring en Python, JSDoc en JS).

### Backend (Python/FastAPI)
- **Nomenclatura:** Usar `snake_case` para variables y nombres de funciones.
- **Tipado:** Usar Type Hints de Python obligatoriamente.
- **Estructura:** Seguir principios REST para los endpoints.

### Frontend (JS/HTML/CSS)
- **Nomenclatura:** Usar `camelCase` para variables y funciones en JavaScript.
- **Diseño:** Estilo "Mobile First" simulando una interfaz de chat (estilo WhatsApp) con burbujas verdes/blancas.
- **PWA:** El código debe ser compatible para instalarse como App (manifest.json).

### Base de Datos (SQL/Supabase)
- **Seguridad (CRÍTICO):** Todas las consultas deben respetar las políticas RLS (Row Level Security). Nunca generar consultas que ignoren el `auth.uid()` del usuario, excepto para la tabla pública `catalogo_universal`.
- **IDs:** Usar siempre UUIDs (`uuid-ossp`).

## 4. CONTEXTO DE LA BASE DE DATOS (Fuente de Verdad)
La estructura de la base de datos ya está definida en `sql 1.txt`. La IA debe asumir este esquema y no inventar tablas nuevas sin permiso:

1.  **public.catalogo_universal:** Catálogo maestro de productos (Solo lectura para usuarios). Campos: `id`, `nombre`, `categoria`, `codigo_barra`.
2.  **public.profiles:** Perfiles de negocio vinculados a `auth.users`.
3.  **public.inventario_local:** Stock específico de cada usuario. Relaciona `user_id` con `producto_id` del catálogo universal.
4.  **public.ventas:** Registro histórico.
    *   **Nota importante:** El campo `detalles` es tipo `JSONB` y debe seguir la estructura: `[{"prod": "Nombre", "cant": 1}]`.
5.  **public.suscripciones:** Estado del pago del usuario (integración futura con Flow/Stripe).

## 5. INSTRUCCIONES ESPECÍFICAS PARA LA IA
- Si vas a generar una query para ventas, recuerda insertar en `public.ventas` y actualizar `public.inventario_local` simultáneamente.
- Para el procesamiento de IA, el input es un archivo de audio (.webm) y el output esperado del backe


# para el user de prueba: 2fc6fdae-7eb2-44eb-a3f6-b2810d88c430