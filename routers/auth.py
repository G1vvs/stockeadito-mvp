from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from database import supabase
from typing import List, Optional

router = APIRouter(tags=["Auth"])

class UserRegister(BaseModel):
    email: str
    password: str
    nombre_negocio: str

@router.post("/auth/register")
def register_user(user: UserRegister):
    try:
        # 👇 Limpiamos el correo de espacios accidentales al inicio o al final 👇
        email_limpio = user.email.strip()

        # crear usuario en supabase auth
        response = supabase.auth.sign_up({
            "email": email_limpio,  # Usamos la variable limpia aquí
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
        # 1. Imprimimos el error con un emoji para verlo facilísimo en la terminal
        print(f"🕵️‍♂️ ERROR REAL DE SUPABASE: {str(e)}")
        
        # 2. Lo mandamos como error 400 (Bad Request) porque es un error de validación, no del servidor
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

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

@router.get("/tutoriales", response_model=List[dict])
def obtener_tutoriales():
    try:
        # Traemos los videos ordenados para que el usuario aprenda paso a paso
        response = supabase.table("tutoriales").select("*").order("orden").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

