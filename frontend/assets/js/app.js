// frontend/assets/js/app.js

const BACKEND_URL = 'http://localhost:8000';
const token = localStorage.getItem('token');
const user = JSON.parse(localStorage.getItem('user') || '{}');

// 1. VALIDACIÓN DE SEGURIDAD
if (!token) {
    window.location.href = '/'; // Si no hay token, al login
}

// 2. INICIALIZACIÓN
document.addEventListener('DOMContentLoaded', () => {
    if (user.email) document.getElementById('userEmail').innerText = user.email;
    checkStatus();
    loadInventory(); // Cargar la tabla al iniciar

    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }
});

// ==========================================
// 📦 FUNCIONES DE INVENTARIO (TABLA)
// ==========================================

async function loadInventory() {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
        const response = await fetch(`${BACKEND_URL}/api/inventory`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            const products = await response.json();
            renderTable(products);
        }
    } catch (error) {
        console.error("Error inventario:", error);
    }
}

function renderTable(products) {
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';

    if (!products || products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Inventario vacío</td></tr>';
        return;
    }

    products.forEach(p => {
        const nombreOriginal = p.catalogo_universal ? p.catalogo_universal.nombre : 'Producto';
        const nombreSafe = nombreOriginal.replace(/'/g, "\\'"); 

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${nombreOriginal}</td>
            <td style="text-align:center; font-weight:bold;">${p.stock_actual}</td>
            <td style="text-align:right;">$${p.precio_venta.toLocaleString('es-CL')}</td>
            <td style="text-align:center;">
                <button class="action-btn btn-edit" 
                    onclick="editarProducto('${p.id}', '${nombreSafe}', ${p.stock_actual}, ${p.precio_venta})" 
                    title="Editar">✏️
                </button>
                
                <button class="action-btn btn-delete" 
                    onclick="eliminarProducto('${p.id}', '${nombreSafe}')" 
                    title="Eliminar">🗑️
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// 👇 ESTAS SON LAS FUNCIONES QUE TE FALTAN PARA QUE LOS BOTONES FUNCIONEN 👇

window.editarProducto = async function(id, nombre, stock, precio) {
    const nuevoStock = prompt(`Editar Stock para ${nombre}:`, stock);
    if (nuevoStock === null) return;
    
    const nuevoPrecio = prompt(`Editar Precio para ${nombre}:`, precio);
    if (nuevoPrecio === null) return;

    try {
        const response = await fetch(`${BACKEND_URL}/api/inventory/${id}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                stock_actual: parseInt(nuevoStock),
                precio_venta: parseInt(nuevoPrecio)
            })
        });

        if (response.ok) {
            alert("✅ Actualizado");
            loadInventory();
        } else {
            alert("❌ Error al actualizar");
        }
    } catch (e) { alert("Error de conexión"); }
};

window.eliminarProducto = async function(id, nombre) {
    if(!confirm(`⚠️ ¿Eliminar "${nombre}"?`)) return;

    try {
        const response = await fetch(`${BACKEND_URL}/api/inventory/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });

        if (response.ok) {
            alert("🗑️ Eliminado");
            loadInventory();
        } else {
            alert("❌ Error al eliminar");
        }
    } catch (e) { alert("Error de conexión"); }
};

// ==========================================
// 💬 FUNCIONES DE CHAT & OTROS
// ==========================================

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    appendMessage(msg, 'user');
    input.value = '';
    const loadId = appendMessage('...', 'bot', true);

    try {
        const res = await fetch(`${BACKEND_URL}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({ message: msg })
        });
        const data = await res.json();
        removeMessage(loadId);
        appendMessage(data.reply || "Error", 'bot');
        if (res.ok) loadInventory();
    } catch (e) {
        removeMessage(loadId);
        appendMessage("Error de conexión", 'bot');
    }
}

function appendMessage(text, sender, isTemp=false) {
    const box = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    if(isTemp) div.id = 'temp';
    div.innerText = text;
    box.appendChild(div);
    return div.id;
}
function removeMessage(id) { const el = document.getElementById(id); if(el) el.remove(); }
function checkStatus() { document.getElementById('statusContainer').innerHTML = '<span class="status-badge premium">Premium</span>'; }
function logout() { localStorage.clear(); window.location.href = '/'; }