import os
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from openai import OpenAI

#iniciamos el cliente openai
client = OpenAI()

router = APIRouter(
    tags=["Artificial Intelligence"]
)

#MODELO
class ChatRequest(BaseModel):
    message: str

# endpoint de prueba

@router.post("/chat/test")
def test_ai_connection(request: ChatRequest):
    '''
    Envia un mensaje simple a chatgpt-4o-mini para verificar
    '''
    try:
        print(f"Enviado a OpenAI: {request.message}")
        completion = client.chat.completions.create(
            model = "gpt-4o-mini", # usamos el modelo barato
            messages=[
                {"role": "system", "content": "Eres un asistente útil de un minimarket chileno."},
                {"role": "user", "content": request.message}
            ]
        )
        response_text = completion.choices[0].message.content
        return {"reply": response_text}
    
    except Exception as e:
        print(f"Error OpenAI: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=str(e))