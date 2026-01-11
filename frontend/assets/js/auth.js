// assets/js/auth.js

// URL del Backend (Cámbiala cuando subas a producción)
const BACKEND_URL = 'http://localhost:8000'; 

// ==========================================
// LÓGICA DE MODALES
// ==========================================

function openModal(type) {
    const modal = document.getElementById('authModal');
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    
    modal.classList.add('active');
    
    if (type === 'login') {
        loginForm.style.display = 'block';
        signupForm.style.display = 'none';
    } else {
        signupForm.style.display = 'block';
        loginForm.style.display = 'none';
    }
}

function closeModal() {
    document.getElementById('authModal').classList.remove('active');
}

function switchToLogin() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('signupForm').style.display = 'none';
}

function switchToSignup() {
    document.getElementById('signupForm').style.display = 'block';
    document.getElementById('loginForm').style.display = 'none';
}

// Cerrar modal al hacer click fuera
document.getElementById('authModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeModal();
    }
});

function scrollToSection(id) {
    document.getElementById(id).scrollIntoView({ behavior: 'smooth' });
}

// ==========================================
// CONEXIÓN CON BACKEND (Login y Registro)
// ==========================================

async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const response = await fetch(`${BACKEND_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            // 1. Obtenemos el token
            const token = data.access_token;
            
            if (token) {
                localStorage.setItem('token', token); 

                // 2. CORRECCIÓN IMPORTANTE:
                // Tu backend no devuelve "data.user", devuelve "data.user_id".
                // Construimos el objeto nosotros mismos para que app.js no falle.
                const usuarioParaGuardar = {
                    email: email,      // Usamos el email que escribió en el formulario
                    id: data.user_id   // Usamos el ID que nos dio el backend
                };

                localStorage.setItem('user', JSON.stringify(usuarioParaGuardar));
                
                // 3. Redirigimos
                window.location.href = 'dashboard.html';
            }
        } else {
            alert('Error: ' + (data.message || 'Credenciales incorrectas'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión. Verifica que el backend esté corriendo.');
    }
}

async function handleSignup(e) {
    e.preventDefault();
    
    const negocio = document.getElementById('signupNegocio').value;
    const email = document.getElementById('signupEmail').value;
    const password = document.getElementById('signupPassword').value;

    try {
        const response = await fetch(`${BACKEND_URL}/auth/signup`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                email, 
                password,
                nombre_negocio: negocio 
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert('¡Cuenta creada exitosamente! Ahora inicia sesión.');
            switchToLogin();
        } else {
            alert('Error: ' + (data.message || 'No se pudo crear la cuenta'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión. Verifica que el backend esté corriendo.');
    }
}