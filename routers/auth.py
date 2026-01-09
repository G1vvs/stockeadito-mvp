from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from database import supabase

router = APIRouter(tags=["Auth"])

class UserRegister(BaseModel):
    email: str
    password: str
    nombre_negocio: str

@router.post("/auth/register")
def register_user(user: UserRegister):
    try:
        #crear usuario en supabase auth
        response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password,
            "options": {
                "data": {
                    "nombre_negocio": user.nombre_negocio
                }
            }
        })
        # validacion 
        if not response.user:
            # si necesita confirmar el email, el usuario se crea pero no se loguea
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Error al registrar. Revisa si el email ya existe")
        return {
            "msg": "Usuario creado exitosamente.",
            "id": response.user.id,
            "email": response.user.email,
            "negocio": user.nombre_negocio
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=str(e))

class UserLogin(BaseModel):
    email: str
    password: str

@router.post("/auth/login")
def login_user(user: UserLogin):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })
        
        if not response.session:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Error en login")
        return {
            "msg": "Login exitoso",
            "access_token": response.session.access_token,
            "user_id": response.user.id
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Error en login")



