from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import supabase

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Esta funcion se ejecuta Antes de entrar al endpoint protegido
    valida que el token sea real
    """
    token = credentials.credentials
    try: 
        # le enviamos el token a supabase preguntado si el usuario existe y el token es valido
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid Token")
        #si es valido entras
        return user_response.user
    except Exception as e:
        print(f"error: {e}" )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Could not validate credentials")