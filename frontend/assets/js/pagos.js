// frontend/assets/js/pagos.js

const BACKEND_URL = 'http://localhost:8000';
const token = localStorage.getItem('token');
const user = JSON.parse(localStorage.getItem('user') || '{}');

// 1. Verificamos que el usuario realmente haya iniciado sesión
document.addEventListener('DOMContentLoaded', () => {
    if (!token || !user.email) {
        alert("Debes iniciar sesión primero.");
        window.location.href = '/';
    }
});

// 2. Función para conectarse a FastAPI y generar el link
async function procesarPago() {
    const btnPagar = document.getElementById('btnPagar');
    
    // Cambiamos el estado del botón para que el usuario sepa que está cargando
    btnPagar.innerText = "Generando conexión segura...";
    btnPagar.disabled = true;
    btnPagar.style.opacity = "0.7";

    try {
        // Llamamos a la ruta exacta que construiste en Python
        const response = await fetch(`${BACKEND_URL}/pagar/crear-link`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                user_id: user.id || "0",
                email_usuario: user.email,
                precio: 10000
            })
        });

        const data = await response.json();

        if (response.ok && data.url_pago) {
            // ¡ÉXITO! Redirigimos al usuario a la página oficial de MercadoPago
            window.location.href = data.url_pago; 
        } else {
            alert("❌ No se pudo generar el pago: " + (data.detail || "Intenta de nuevo más tarde"));
            restaurarBoton(btnPagar);
        }
    } catch (error) {
        console.error("Error al conectar con el servidor de pagos:", error);
        alert("❌ Error de conexión. Revisa tu internet o intenta de nuevo.");
        restaurarBoton(btnPagar);
    }
}

function restaurarBoton(btn) {
    btn.innerText = "Pagar con MercadoPago";
    btn.disabled = false;
    btn.style.opacity = "1";
}

function cerrarSesion() {
    localStorage.clear();
    window.location.href = '/';
}