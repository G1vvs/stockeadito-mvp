// assets/js/app.js

const BACKEND_URL = 'http://localhost:8000';
const token = localStorage.getItem('token');
const user = JSON.parse(localStorage.getItem('user') || '{}');

// 1. VALIDACIÓN DE SEGURIDAD
if (!token) {
    window.location.href = 'index.html';
}

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    // Mostrar email en header
    if (user.email) document.getElementById('userEmail').innerText = user.email;
    
    // Verificar estado (Free/Premium)
    checkStatus();
    
    // Cargar inventario inicial
    loadInventory();

    // Evento Enter en el chat
    document.getElementById('chatInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
});

// ==========================================
// FUNCIONES DE CHAT
// ==========================================

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    // 🔑 IMPORTANTE: El token debe recuperarse justo antes de enviar
    const token = localStorage.getItem('token'); 

    if (!message) return;

    appendMessage(message, 'user');
    input.value = '';

    const loadingId = appendMessage('Stockeadito está pensando...', 'bot', true);

    try {
        const response = await fetch(`${BACKEND_URL}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Verifica que diga "Bearer " seguido del token
                'Authorization': `Bearer ${token}` 
            },
            body: JSON.stringify({ message: message })
        });

        if (response.status === 401 || response.status === 403) {
            removeMessage(loadingId);
            appendMessage("❌ Sesión expirada o sin permisos. Por favor, re-ingresa.", 'bot');
            return;
        }

        const data = await response.json();
        removeMessage(loadingId);

        if (response.ok) {
            appendMessage(data.reply, 'bot');
            loadInventory(); 
        } else {
            appendMessage("❌ Error: " + (data.detail || "Error en el servidor"), 'bot');
        }
    } catch (error) {
        removeMessage(loadingId);
        appendMessage("❌ Error de conexión con el Backend.", 'bot');
    }
}

function appendMessage(text, sender, isTemp = false) {
    const chatBox = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.classList.add('message', sender);
    if (isTemp) div.id = 'temp-loading';
    div.innerText = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight; // Auto-scroll
    return div.id;
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ==========================================
// FUNCIONES DE INVENTARIO
// ==========================================

async function loadInventory() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }
    try {
        const response = await fetch(`${BACKEND_URL}/api/inventory`, {
            headers: { 
                'Authorization': `Bearer ${token}` 
            }
        });

        if (response.ok) {
            const products = await response.json();
            renderTable(products);
        }
    } catch (error) {
        console.error("Error cargando inventario", error);
    }
}

// Reemplaza esta parte en tu app.js
function renderTable(products) {
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';

    if (!products || products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align:center">Inventario vacío</td></tr>';
        return;
    }

    products.forEach(p => {
        // Acceder al nombre anidado del catálogo
        const nombre = p.catalogo_universal ? p.catalogo_universal.nombre : 'Sin nombre';
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${nombre}</td>
            <td style="font-weight:bold;">${p.stock_actual}</td>
            <td>$${p.precio_venta}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ==========================================
// ESTADO Y PAGOS
// ==========================================

function checkStatus() {
    const container = document.getElementById('statusContainer');
    // Si ya está aquí, asumimos que es premium por el middleware del backend
    container.innerHTML = `<span class="status-badge premium">Plan Premium Activo</span>`;
}

async function comprarPremium() {
    if(!confirm("¿Quieres ir a Mercado Pago para activar tu cuenta?")) return;
    const token = localStorage.getItem('token');
    try {
        const response = await fetch(`${BACKEND_URL}/pagar/crear-link`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({}) // Cuerpo vacío
        });
        
        const data = await response.json();
        if (data.url_pago) {
            window.location.href = data.url_pago;
        } else {
            alert("Error generando link de pago");
        }
    } catch (error) {
        alert("Error de conexión");
    }
}

// ==========================================
// LOGOUT
// ==========================================
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = 'index.html';
}