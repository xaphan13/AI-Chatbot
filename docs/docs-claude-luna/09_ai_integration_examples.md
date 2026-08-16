# Примеры интеграции с AI-моделями

Документ содержит примеры, соответствующие текущему стеку проекта: Python 3.13, FastAPI, `openai.AsyncOpenAI` и GitHub Models API. Примеры с timeout и обработкой ошибок отмечены как рекомендуемое улучшение, потому что в текущем коде эти функции ещё не реализованы.

## 1. Подготовка окружения

Установить зависимости проекта:

```bash
uv sync
```

Создать `.env` в корне проекта:

```env
GITHUB_TOKEN=github_pat_ваш_токен_с_доступом_к_models
SECRET=длинная_случайная_строка_для_jwt
DATABASE_URL=sqlite+aiosqlite:///./sqlite.db
DEBUG=False
```

`GITHUB_TOKEN` необходим для обращения к GitHub Models. Не следует добавлять `.env` или настоящий токен в Git.

Перед запуском приложения применить миграции:

```bash
uv run alembic upgrade head
```

> В текущем состоянии репозитория приложение также пытается монтировать `app/static/`, хотя этот каталог отсутствует. Для запуска необходимо заранее создать пустой каталог `app/static/` либо исправить условное монтирование в `app/main.py`.

## 2. Минимальный прямой вызов модели

Это рабочий шаблон вызова с теми же SDK, base URL, моделью и форматом `messages`, что используются в `app/services/chat.py`:

```python
from openai import AsyncOpenAI


client = AsyncOpenAI(
    api_key="<GITHUB_TOKEN>",
    base_url="https://models.github.ai/inference/",
)


async def ask_model(prompt: str) -> str:
    response = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )
    return response.choices[0].message.content or ""
```

В приложении ключ не передаётся строковым литералом, а читается из `settings.GITHUB_TOKEN`.

## 3. Текущий сервис проекта

Фактический код сервиса:

```python
from openai import AsyncOpenAI

from app.core.config import settings

client = AsyncOpenAI(
    api_key=settings.GITHUB_TOKEN,
    base_url="https://models.github.ai/inference/",
)


async def get_chat_response(prompt: str) -> str:
    message = (
        "Hey ChatGPT, you are a AI chatbot don not tell your name or any personal information. "
        "Here is the prompt you asked for: "
        + prompt
    )
    response = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": message}],
    )
    return response.choices[0].message.content.strip() if response.choices else ""
```

Сервис асинхронный, но пока не имеет timeout, обработки ошибок и отдельного `system` message. Не следует передавать в prompt секреты, пароли или персональные данные без отдельной политики обработки данных.

## 4. Endpoint FastAPI

Текущий endpoint принимает Pydantic-схему и требует авторизованного пользователя:

```python
from fastapi import Body, Depends
from fastapi.routing import APIRouter

from app.api.v1.users import current_user
from app.models.users import User
from app.schemas.chat import ChatRequest
from app.services.chat import get_chat_response

router = APIRouter()


@router.post("/chat")
async def chat_endpoint(
    prompt: ChatRequest = Body(...),
    user: User = Depends(current_user),
):
    response = await get_chat_response(prompt=prompt.prompt)
    return {"response": response}
```

Так как роутер подключён под `/api`, фактический URL — `/api/chat`.

## 5. Пример обращения к API из браузера

Фронтенд отправляет JSON с полем `prompt`. Cookie сессии браузер отправляет автоматически при запросе на тот же origin:

```javascript
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    prompt: 'Объясни разницу между async и sync в Python',
  }),
});

if (!response.ok) {
  throw new Error(`Chat request failed: ${response.status}`);
}

const data = await response.json();
console.log(data.response);
```

Ожидаемый успешный ответ:

```json
{
  "response": "Асинхронный код позволяет ..."
}
```

## 6. Пример через cURL

Сначала нужно получить cookie после входа. Конкретный JWT зависит от пользователя и окружения:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -H 'Cookie: fastapiusersauth=<jwt-cookie-value>' \
  -d '{"prompt":"Что такое dependency injection?"}'
```

Ожидаемый формат ответа:

```json
{"response":"..."}
```

Без cookie или с недействительным JWT API вернёт `401 Unauthorized`.

## 7. Рекомендуемый сервис с timeout и обработкой ошибок

Следующий вариант совместим с тем же OpenAI-compatible API, но делает поведение приложения предсказуемее. Это **пример улучшения**, а не текущая версия файла `app/services/chat.py`.

```python
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from app.core.config import settings


class ChatServiceError(RuntimeError):
    """An error that can be shown as a controlled chat API failure."""


client = AsyncOpenAI(
    api_key=settings.GITHUB_TOKEN,
    base_url="https://models.github.ai/inference/",
    timeout=30.0,
)


async def get_chat_response(prompt: str) -> str:
    try:
        response = await client.chat.completions.create(
            model="openai/gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )
    except APITimeoutError as exc:
        raise ChatServiceError("AI service timed out") from exc
    except RateLimitError as exc:
        raise ChatServiceError("AI service rate limit exceeded") from exc
    except APIConnectionError as exc:
        raise ChatServiceError("Unable to connect to AI service") from exc
    except APIError as exc:
        raise ChatServiceError("AI service returned an error") from exc

    if not response.choices:
        raise ChatServiceError("AI service returned an empty response")

    content = response.choices[0].message.content
    return content.strip() if content else ""
```

Для production этот код нужно дополнить единым exception handler FastAPI, логированием без секретов, ограничением размера prompt и retry только для транзитных ошибок.

## 8. Рекомендуемая параметризация модели

Сейчас модель и `base_url` захардкожены. После добавления настроек в `app/core/config.py` сервис можно сделать provider-neutral в пределах OpenAI-compatible протокола:

```python
from openai import AsyncOpenAI

from app.core.config import settings


client = AsyncOpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
    timeout=settings.LLM_TIMEOUT,
)


async def get_chat_response(prompt: str) -> str:
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": settings.LLM_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )
    return response.choices[0].message.content or ""
```

Пример настроек:

```python
class Setting(BaseSettings):
    LLM_API_KEY: str
    LLM_BASE_URL: str = "https://models.github.ai/inference/"
    LLM_MODEL: str = "openai/gpt-4o"
    LLM_SYSTEM_PROMPT: str = "You are a helpful assistant."
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1000
    LLM_TIMEOUT: float = 30.0
```

После этого можно менять модель и OpenAI-compatible endpoint через `.env`, не редактируя бизнес-логику. Значения параметров нужно сверять с возможностями конкретной модели и провайдера.

## 9. Пример multi-turn после добавления истории

Текущая API-схема принимает только строку и не сохраняет контекст. OpenAI-compatible endpoint поддерживает массив сообщений, поэтому после создания `Conversation`/`Message` можно передавать историю:

```python
from collections.abc import Sequence

from openai import AsyncOpenAI


async def ask_with_history(
    client: AsyncOpenAI,
    messages: Sequence[dict[str, str]],
) -> str:
    response = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=list(messages),
    )
    return response.choices[0].message.content or ""


messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Меня зовут Алексей."},
    {"role": "assistant", "content": "Приятно познакомиться!"},
    {"role": "user", "content": "Как меня зовут?"},
]
```

Этот фрагмент показывает формат будущего вызова; сам проект пока не содержит таблиц conversations/messages и не передаёт такой список.

## 10. Пример streaming через SSE

Streaming в текущем приложении не включён. Возможная реализация на основе того же SDK:

```python
import json
from collections.abc import AsyncIterator

from openai import AsyncOpenAI


async def stream_chat_response(
    client: AsyncOpenAI,
    prompt: str,
) -> AsyncIterator[str]:
    stream = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )

    async for chunk in stream:
        if not chunk.choices:
            continue
        content = chunk.choices[0].delta.content
        if content:
            yield f"data: {json.dumps({'content': content})}\n\n"

    yield "data: [DONE]\n\n"
```

Подключение к FastAPI:

```python
from fastapi.responses import StreamingResponse


@router.post("/chat/stream")
async def stream_chat(prompt: ChatRequest = Body(...)):
    return StreamingResponse(
        stream_chat_response(client, prompt.prompt),
        media_type="text/event-stream",
    )
```

Для защищённого production endpoint также нужно добавить `Depends(current_user)`, обработку отключения клиента и лимиты продолжительности stream.

## 11. Концептуальный пример мультиагентного workflow

Ниже — минимальная иллюстрация оркестрации нескольких ролей. Это не часть текущего приложения и не готовая production-функция: в ней отсутствуют persistence, permission model, retries, moderation и контроль бюджета.

```python
import asyncio

from openai import AsyncOpenAI


async def run_agent(
    client: AsyncOpenAI,
    system_prompt: str,
    task: str,
) -> str:
    response = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task},
        ],
    )
    return response.choices[0].message.content or ""


async def run_multi_agent_task(client: AsyncOpenAI, task: str) -> str:
    research, critique = await asyncio.gather(
        run_agent(client, "You are a research agent.", task),
        run_agent(client, "You are a critical reviewer. Identify risks.", task),
    )

    synthesis_prompt = f"""
Task:
{task}

Research result:
{research}

Critique result:
{critique}

Synthesize a concise, well-supported final answer.
"""
    return await run_agent(
        client,
        "You are the final synthesis agent.",
        synthesis_prompt,
    )
```

Безопасные правила для такого workflow:

- ограничить число агентов, шагов, токенов и общее время;
- не считать вывод одного агента доверенной инструкцией;
- отделять данные от инструкций и проверять результаты;
- не давать агентам опасные инструменты без явного разрешения;
- сохранять trace каждого вызова и стоимость;
- использовать последовательное выполнение, если шаг зависит от результата другого;
- использовать ограниченный параллелизм только для независимых задач.

## 12. Проверка и запуск

Запустить приложение:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Проверить документацию API:

```text
http://localhost:8000/docs
```

Проверить чат можно после регистрации и входа в браузере. Автоматические тесты AI-интеграции в проекте пока отсутствуют. Рекомендуемый тест должен мокировать `client.chat.completions.create`, чтобы тесты не зависели от сети, токена и лимитов GitHub Models.
