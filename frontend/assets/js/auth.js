// assets/js/auth.js

const BACKEND_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://stockeadito-mvp.onrender.com';

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

document.getElementById('authModal').addEventListener('click', function(e) {
    if (e.target === this) closeModal();
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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            const token = data.access_token;
            if (token) {
                localStorage.setItem('token', token);
                localStorage.setItem('user', JSON.stringify({
                    email: email,
                    id: data.user_id
                }));
                // ✅ FIX: extensión explícita para Vercel
                window.location.href = '/dashboard.html';
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
        const response = await fetch(`${BACKEND_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, nombre_negocio: negocio })
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
