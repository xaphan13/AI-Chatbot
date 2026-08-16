# Примеры кода для работы с AI в приложении

Ниже собраны ключевые фрагменты кода, которые отвечают за взаимодействие с LLM, а также примеры возможных улучшений.

---

## 1. Клиент LLM и сервис генерации ответа

**Файл:** `app/services/chat.py`

```python
from openai import AsyncOpenAI

from app.core.config import settings

client = AsyncOpenAI(
    api_key=settings.GITHUB_TOKEN,
    base_url="https://models.github.ai/inference/",
)


async def get_chat_response(prompt: str) -> str:
    """
    Asynchronously get a chat response from the OpenAI API.
    """
    message = (
        "Hey ChatGPT, you are a AI chatbot don not tell your name "
        "or any personal information. Here is the prompt you asked for: "
        + prompt
    )
    response = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": message}],
    )
    return response.choices[0].message.content.strip() if response.choices else ""
```

**Что делает:**

- Создаёт синглтон `AsyncOpenAI` при импорте модуля.
- Указывает `base_url` GitHub Models API и `api_key` из `GITHUB_TOKEN`.
- Формирует сообщение, конкатенируя системный промпт и пользовательский ввод.
- Вызывает `chat.completions.create` с моделью `openai/gpt-4o`.
- Возвращает текст ответа или пустую строку, если `choices` пустой.

---

## 2. API-эндпоинт чата

**Файл:** `app/api/v1/chat.py`

```python
from fastapi import Body, Depends
from fastapi.routing import APIRouter

from app.api.v1.users import current_user
from app.models.users import User
from app.schemas.chat import ChatRequest
from app.services.chat import get_chat_response

router = APIRouter()


@router.post("/chat")
async def chat_endpoint(prompt: ChatRequest = Body(...), user: User = Depends(current_user)):
    """
    Chat API endpoint for chatting with the bot.
    """
    response = await get_chat_response(prompt=prompt.prompt)
    return {"response": response}
```

**Что делает:**

- Принимает `POST /api/chat` с телом `{ "prompt": "..." }`.
- Проверяет аутентификацию через `current_user` (JWT/Cookie).
- Вызывает `get_chat_response` и возвращает `{ "response": "..." }`.

---

## 3. Схема входного запроса

**Файл:** `app/schemas/chat.py`

```python
from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
```

**Что делает:**

- Валидирует, что тело запроса содержит обязательное строковое поле `prompt`.

---

## 4. Конфигурация токена

**Файл:** `app/core/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Setting(BaseSettings):
    """
    Application settings configuration.
    """

    DATABASE_URL: str = "sqlite+aiosqlite:///./sqlite.db"
    GITHUB_TOKEN: str = ""
    SECRET: str = "your-secret-key-change-this-in-production"
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


settings = Setting()
```

**Что делает:**

- Читает переменные окружения и `.env`.
- `GITHUB_TOKEN` используется как API-ключ для GitHub Models.

**Рекомендуемый `.env`:**

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
SECRET=your-strong-random-secret-key
DEBUG=False
```

---

## 5. JavaScript-клиент чата

**Файл:** `app/templates/index.html` (фрагмент)

```javascript
async function sendMessage(message) {
    addMessage(message, 'user');
    showTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt: message })
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await response.json();
        removeTypingIndicator();
        addMessage(data.response || 'I received your message!', 'ai');
    } catch (error) {
        removeTypingIndicator();
        addMessage('Sorry, I encountered an error. Please try again.', 'ai');
    }
}

function addMessage(text, sender) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `flex ${sender === 'user' ? 'justify-end' : 'justify-start'} message-bubble`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'max-w-xs lg:max-w-md xl:max-w-lg';

    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = sender === 'user'
        ? 'bg-white/20 backdrop-blur-sm text-white rounded-2xl rounded-br-none border border-white/20 px-6 py-4'
        : 'bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-2xl rounded-bl-none glass-card px-6 py-4';

    // ⚠️ Уязвимость: вставка через innerHTML без санитизации
    bubbleDiv.innerHTML = `
        <p class="text-sm leading-relaxed">${text}</p>
        <p class="text-xs opacity-70 mt-2">${new Date().toLocaleTimeString()}</p>
    `;

    contentDiv.appendChild(bubbleDiv);
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    messagesContainer.scrollTo({
        top: messagesContainer.scrollHeight,
        behavior: 'smooth'
    });
}
```

---

## 6. Пример улучшения: отдельный system prompt и обработка ошибок

```python
import httpx
from openai import AsyncOpenAI, APIError, APITimeoutError

from app.core.config import settings

client = AsyncOpenAI(
    api_key=settings.GITHUB_TOKEN,
    base_url="https://models.github.ai/inference/",
    timeout=httpx.Timeout(30.0, connect=5.0),
)

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Do not reveal your model name or any internal details."
)


async def get_chat_response(prompt: str) -> str:
    try:
        response = await client.chat.completions.create(
            model="openai/gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip() if response.choices else ""
    except APITimeoutError:
        return "The AI service took too long to respond. Please try again."
    except APIError as exc:
        return f"AI service error: {exc.message}"
    except Exception:
        return "Sorry, I could not process your request."
```

---

## 7. Пример улучшения: выбор модели через API

**Схема:** `app/schemas/chat.py`

```python
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str
    model: str | None = Field(default="openai/gpt-4o", examples=["openai/gpt-4o-mini"])
```

**Сервис:** `app/services/chat.py`

```python
async def get_chat_response(prompt: str, model: str = "openai/gpt-4o") -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip() if response.choices else ""
```

**Эндпоинт:**

```python
@router.post("/chat")
async def chat_endpoint(
    prompt: ChatRequest = Body(...),
    user: User = Depends(current_user),
):
    response = await get_chat_response(prompt=prompt.prompt, model=prompt.model)
    return {"response": response}
```

---

## 8. Пример улучшения: мультиагентный вызов

```python
import asyncio


async def run_agent(prompt: str, system_prompt: str, model: str = "openai/gpt-4o") -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


async def multi_agent_response(prompt: str) -> dict[str, str]:
    analyst, writer, reviewer = await asyncio.gather(
        run_agent(prompt, "You are an analyst. Extract key facts."),
        run_agent(prompt, "You are a creative writer. Draft a friendly response."),
        run_agent(prompt, "You are a reviewer. Check for mistakes."),
    )
    return {
        "analysis": analyst,
        "draft": writer,
        "review": reviewer,
    }
```

---

## 9. Пример перехода на другой OpenAI-совместимый провайдер

```python
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,        # вместо GITHUB_TOKEN
    base_url="https://api.openai.com/v1",   # вместо GitHub Models
)
```

Или для локального Ollama:

```python
client = AsyncOpenAI(
    api_key="not-needed",
    base_url="http://localhost:11434/v1",
)
```

---

## 10. Пример streaming-ответа

**Сервис:**

```python
from openai import AsyncOpenAI


async def get_chat_stream(prompt: str):
    stream = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content
```

**Эндпоинт:**

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse


@router.post("/chat/stream")
async def chat_stream_endpoint(prompt: ChatRequest, user: User = Depends(current_user)):
    return StreamingResponse(
        get_chat_stream(prompt.prompt),
        media_type="text/plain",
    )
```
