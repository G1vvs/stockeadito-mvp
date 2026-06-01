const BACKEND_URL = 'http://localhost:8000';
const token = localStorage.getItem('token');
const user = JSON.parse(localStorage.getItem('user') || '{}');

// 1. VALIDACIÓN DE SEGURIDAD
if (!token) {
    window.location.href = '/'; 
}

// 2. INICIALIZACIÓN
document.addEventListener('DOMContentLoaded', () => {
    if (user.email) document.getElementById('userEmail').innerText = user.email;
    checkStatus();
    loadInventory(); 
    loadMetrics(); // 👈 ¡ESTA ES LA LÍNEA MÁGICA QUE FALTABA!

    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    const categoryFilter = document.getElementById('categoryFilter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', function(e) {
            const categoriaElegida = e.target.value;
            const filasTabla = document.querySelectorAll('#tableBody tr');
            filasTabla.forEach(fila => {
                if (!fila.hasAttribute('data-categoria')) return;
                const categoriaFila = fila.getAttribute('data-categoria');
                if (categoriaElegida === 'all' || categoriaFila === categoriaElegida) {
                    fila.style.display = ''; 
                } else {
                    fila.style.display = 'none'; 
                }
            });
        });
    }
});

// ==========================================
// 📊 FUNCIONES DE MÉTRICAS (DASHBOARD)
// ==========================================
let topProductosChartInstance = null; // Variable global para el gráfico

async function loadMetrics() {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
        const response = await fetch(`${BACKEND_URL}/api/stats?t=${new Date().getTime()}`, {
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Cache-Control': 'no-cache'
            }
        });

        if (response.ok) {
            const stats = await response.json();
            
            // Si el backend nos avisa de un error de BD, lo mostramos en consola
            if (stats.error_detalle) {
                console.error("⚠️ Error de base de datos en /stats:", stats.error_detalle);
                console.error("👉 Verifica en Supabase que la tabla se llame exactamente 'ventas'");
            }
            
            // Llenar tarjetas numéricas
            document.getElementById('ventas-hoy').innerText = `$${stats.ventas_hoy.toLocaleString('es-CL')}`;
            document.getElementById('cantidad-vendida').innerText = stats.productos_vendidos;
            document.getElementById('alertas-stock').innerText = stats.alertas_stock;

            // 📊 DIBUJAR EL GRÁFICO 📊
            const ctx = document.getElementById('topProductosChart').getContext('2d');
            
            // Si ya hay un gráfico viejo, lo borramos para no encimar colores
            if (topProductosChartInstance) {
                topProductosChartInstance.destroy();
            }

            // Creamos el gráfico nuevo
            topProductosChartInstance = new Chart(ctx, {
                type: 'bar', // Gráfico de barras
                data: {
                    labels: stats.chart_labels, // ["Sprite", "Pan", ...]
                    datasets: [{
                        label: 'Unidades Vendidas Hoy',
                        data: stats.chart_data, // [3, 1, ...]
                        backgroundColor: '#3498db',
                        borderRadius: 5
                    }]
                },
                options: {
                    responsive: true,
                    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
                }
            });
        }
    } catch (error) {
        console.error("Error al cargar métricas:", error);
    }
}

// ==========================================
// 📦 FUNCIONES DE INVENTARIO (TABLA)
// ==========================================

async function loadInventory() {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
        // 👇 EL TRUCO: Le agregamos la hora exacta al final de la URL 👇
        const urlFresca = `${BACKEND_URL}/api/inventory?t=${new Date().getTime()}`;
        
        const response = await fetch(urlFresca, {
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Cache-Control': 'no-cache' // Le prohibimos usar la memoria vieja
            }
        });

        if (response.status === 403) {
            window.location.href = '/pagos.html'; 
            return; 
        }

        if (response.ok) {
            const products = await response.json();
            renderTable(products);
            cargarFiltroCategorias(products); 
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
        const categoriaProducto = p.catalogo_universal ? (p.catalogo_universal.categoria || 'Otros') : (p.categoria || 'Otros');

        const tr = document.createElement('tr');
        tr.setAttribute('data-categoria', categoriaProducto); 
        
        tr.innerHTML = `
            <td>
                ${nombreOriginal}
                <div style="font-size: 0.75rem; color: #888; margin-top: 2px;">${categoriaProducto}</div>
            </td>
            <td style="text-align:center; font-weight:bold;">${p.stock_actual}</td>
            <td style="text-align:right;">$${p.precio_venta.toLocaleString('es-CL')}</td>
            <td style="text-align:center;">
                <button class="action-btn btn-edit" onclick="editarProducto('${p.id}', '${nombreSafe}', ${p.stock_actual}, ${p.precio_venta})" title="Editar">✏️</button>
                <button class="action-btn btn-delete" onclick="eliminarProducto('${p.id}', '${nombreSafe}')" title="Eliminar">🗑️</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function cargarFiltroCategorias(products) {
    const selectFiltro = document.getElementById('categoryFilter');
    if (!selectFiltro) return;
    selectFiltro.innerHTML = '<option value="all">📦 Todas las categorías</option>';

    const categoriasBrutas = products.map(p => {
        return p.catalogo_universal ? (p.catalogo_universal.categoria || 'Otros') : (p.categoria || 'Otros');
    });

    const categoriasUnicas = [...new Set(categoriasBrutas)].sort();
    categoriasUnicas.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat;
        option.textContent = cat;
        selectFiltro.appendChild(option);
    });
}

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
            loadInventory();
        } else {
            alert("❌ Error al eliminar");
        }
    } catch (e) { alert("Error de conexión"); }
};

// ==========================================
// 💬 FUNCIONES DE CHAT
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
        
        if (res.ok) {
            loadInventory(); 
            loadMetrics(); // 👈 RECARGAMOS LAS MÉTRICAS TRAS CADA VENTA
        }
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

// ==========================================
// 🎤 FUNCIONES DE AUDIO
// ==========================================
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

window.toggleRecording = async function() {
    const micBtn = document.getElementById('micButton');

    if (isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        micBtn.style.backgroundColor = ""; 
        micBtn.innerHTML = "🎤"; 
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            if (event.data.size > 0) audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await enviarAudioAlBackend(audioBlob);
        };

        mediaRecorder.start();
        isRecording = true;
        micBtn.style.backgroundColor = "#ff4444"; 
        micBtn.innerHTML = "⏹️"; 
        
    } catch (error) {
        alert("No se pudo acceder al micrófono.");
    }
};

async function enviarAudioAlBackend(audioBlob) {
    const loadId = appendMessage('Escuchando...', 'bot', true);
    const formData = new FormData();
    formData.append("file", audioBlob, "audio.webm");

    try {
        const res = await fetch(`${BACKEND_URL}/api/transcribe`, { 
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
            body: formData
        });
        
        const data = await res.json();
        removeMessage(loadId);
        
        if (res.ok && data.text) {
            const input = document.getElementById('chatInput');
            input.value = data.text;
            sendMessage(); 
        } else {
            appendMessage("No entendí el audio. Intenta de nuevo.", 'bot');
        }
    } catch (e) {
        removeMessage(loadId);
        appendMessage("Error al enviar el audio.", 'bot');
    }
}