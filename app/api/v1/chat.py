from fastapi.routing import APIRouter
from fastapi import Body, Depends

from app.models.users import User
from app.services.chat import get_chat_response
from app.schemas.chat import ChatRequest
from app.api.v1.users import current_user


router = APIRouter()


@router.post("/chat")
async def chat_endpoint(prompt: ChatRequest = Body(...), user: User = Depends(current_user)):
    """
    Chat API endpoint for chatting with the bot.
    """
    response = await get_chat_response(prompt=prompt.prompt)
    return {"response": response}