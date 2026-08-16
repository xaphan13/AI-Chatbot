# 09 — Примеры кода для работы с AI

Примеры разделены на две группы:

- **Текущая реализация** — код соответствует файлам проекта и может использоваться уже сейчас.
- **Расширение** — рабочие заготовки для функций, которых в текущем приложении ещё нет.

Во всех примерах токены задаются через переменные окружения. Реальные секреты в код и документацию добавлять нельзя.

## 1. Текущий вызов модели через `AsyncOpenAI`

Это фактический вариант из `app/services/chat.py`:

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

### Что делает пример

1. Создаёт асинхронный OpenAI-совместимый клиент.
2. Подключает его к GitHub Models API через `base_url`.
3. Передаёт API-токен из `GITHUB_TOKEN`.
4. Отправляет одну реплику в Chat Completions API.
5. Возвращает текст первого ответа модели.

В текущем варианте нет timeout, retry, обработки ошибок и передачи истории.

## 2. Endpoint приложения FastAPI

Фактический endpoint находится в `app/api/v1/chat.py`:

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

Роутер подключён в `app/main.py` с prefix `/api`, поэтому полный адрес — `POST /api/chat`.

## 3. Запрос из браузера

Фрагмент, соответствующий клиенту из `app/templates/index.html`:

```javascript
const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({ prompt: message })
});

if (response.status === 401) {
    window.location.href = '/login';
    return;
}

if (!response.ok) {
    throw new Error('AI request failed');
}

const data = await response.json();
addMessage(data.response || 'I received your message!', 'ai');
```

Cookie `fastapiusersauth` добавляется браузером автоматически, если пользователь уже вошёл в систему.

## 4. Проверка API через `curl`

Для cookie-аутентификации сначала нужно получить cookie после входа. Конкретный способ получения cookie зависит от выбранной auth-схемы и окружения. Если имеется действующая cookie, запрос выглядит так:

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -H "Cookie: fastapiusersauth=<JWT_COOKIE_VALUE>" \
  -d '{"prompt":"Составь краткое описание FastAPI"}'
```

Ожидаемый формат успешного ответа:

```json
{
  "response": "FastAPI — это ..."
}
```

Не передавайте токен или cookie в публичные issue, логи и скриншоты.

## 5. Рекомендуемый вариант с ролями `system` и `user`

**Расширение, не реализованное в текущем коде.** Отдельные роли лучше, чем конкатенация инструкции и запроса в одну строку:

```python
async def get_chat_response(prompt: str) -> str:
    response = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a concise and helpful assistant.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    return response.choices[0].message.content.strip() if response.choices else ""
```

Это не устраняет prompt injection автоматически, но делает структуру инструкций явной и облегчает дальнейшее управление контекстом.

## 6. Передача истории диалога

**Расширение, не реализованное в текущем коде.** Если история хранится в базе или приходит от доверенного backend-компонента, она может быть преобразована в список сообщений:

```python
from collections.abc import Sequence


async def get_chat_response(
    prompt: str,
    history: Sequence[dict[str, str]] = (),
) -> str:
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. Answer in Russian.",
        },
        *history,
        {"role": "user", "content": prompt},
    ]

    response = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=messages,
    )
    return response.choices[0].message.content.strip() if response.choices else ""
```

Перед использованием нужно валидировать роли, ограничивать размер истории и хранить сообщения с привязкой к пользователю/диалогу. Нельзя без ограничений принимать произвольную историю от клиента.

Пример допустимой истории:

```python
history = [
    {"role": "user", "content": "Что такое FastAPI?"},
    {"role": "assistant", "content": "FastAPI — веб-фреймворк для Python."},
]
```

## 7. Конфигурируемая модель и провайдер

**Расширение, не реализованное в текущем коде.** Сначала параметры можно вынести в настройки:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Setting(BaseSettings):
    GITHUB_TOKEN: str = ""
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://models.github.ai/inference/"
    LLM_MODEL: str = "openai/gpt-4o"
    LLM_TIMEOUT: float = 30.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
```

Затем клиент может быть создан так:

```python
from openai import AsyncOpenAI


api_key = settings.LLM_API_KEY or settings.GITHUB_TOKEN

client = AsyncOpenAI(
    api_key=api_key,
    base_url=settings.LLM_BASE_URL,
    timeout=settings.LLM_TIMEOUT,
)

response = await client.chat.completions.create(
    model=settings.LLM_MODEL,
    messages=[{"role": "user", "content": "Привет!"}],
)
```

Поддержка конкретной модели определяется не SDK, а каталогом и условиями выбранного провайдера. Перед переключением нужно проверить название модели, endpoint, авторизацию и доступные параметры.

## 8. Обработка ошибок и timeout

**Расширение, не реализованное в текущем коде.** Минимальный вариант обработки ошибок:

```python
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    RateLimitError,
)


async def safe_chat_response(prompt: str) -> str:
    try:
        response = await client.chat.completions.create(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        )
    except APITimeoutError as error:
        raise RuntimeError("AI service timed out") from error
    except RateLimitError as error:
        raise RuntimeError("AI rate limit exceeded") from error
    except APIConnectionError as error:
        raise RuntimeError("Cannot connect to AI service") from error
    except APIError as error:
        raise RuntimeError("AI provider returned an error") from error

    return response.choices[0].message.content.strip() if response.choices else ""
```

Для production также нужны структурированное логирование, ограничение длины prompt, retry только для безопасных случаев и единый формат ошибок API.

## 9. Streaming-ответ

**Расширение, не реализованное в текущем коде.** OpenAI-совместимый API может поддерживать streaming:

```python
async def stream_chat_response(prompt: str):
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
            yield content
```

На стороне FastAPI такой генератор нужно обернуть в `StreamingResponse` с согласованным форматом, например `text/event-stream`. Текущий frontend ожидает обычный JSON через `response.json()`, поэтому для streaming потребуется изменить и backend, и JavaScript-клиент.

## 10. Что важно проверить перед внедрением примеров

- Не использовать реальный токен в исходном коде.
- Не считать любой OpenAI-совместимый endpoint полностью взаимозаменяемым: могут отличаться модели, лимиты, параметры и формат ошибок.
- Не принимать историю сообщений и настройки модели от клиента без валидации.
- Не вставлять ответ модели через `innerHTML`; для обычного текста использовать `textContent`.
- Добавить timeout до включения AI-функции в production.
