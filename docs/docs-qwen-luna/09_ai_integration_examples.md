# Примеры кода для работы с AI

Этот файл содержит примеры, основанные на текущей интеграции проекта, а также безопасные направления расширения. Примеры расширения не являются уже реализованными функциями приложения.

## 1. Текущий вызов AI через GitHub Models

Фактическая реализация находится в `app/services/chat.py`:

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

## 2. Текущий API-эндпоинт чата

`app/api/v1/chat.py` принимает JSON с полем `prompt` и возвращает JSON с полем `response`:

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

Пример запроса:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -H 'Cookie: fastapiusersauth=<JWT>' \
  -d '{"prompt":"Составь краткое описание FastAPI"}'
```

## 3. Вызов API напрямую через OpenAI SDK

Такой код соответствует используемому в проекте протоколу:

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="<PROVIDER_TOKEN>",
    base_url="https://models.github.ai/inference/",
)

response = await client.chat.completions.create(
    model="openai/gpt-4o",
    messages=[
        {"role": "system", "content": "Отвечай кратко и на русском языке."},
        {"role": "user", "content": "Что такое dependency injection?"},
    ],
)

answer = response.choices[0].message.content or ""
```

В отличие от текущего кода, здесь системная инструкция передаётся отдельным сообщением с ролью `system`. Это предпочтительный формат при развитии сервиса.

## 4. Передача истории диалога

Сейчас история не хранится и не передаётся. Для одного запроса с контекстом можно использовать список сообщений:

```python
messages = [
    {"role": "system", "content": "Ты полезный ассистент."},
    {"role": "user", "content": "Меня зовут Анна."},
    {"role": "assistant", "content": "Приятно познакомиться, Анна."},
    {"role": "user", "content": "Как меня зовут?"},
]

response = await client.chat.completions.create(
    model="openai/gpt-4o",
    messages=messages,
)
```

Для реального приложения `messages` следует получать из БД по идентификатору беседы, ограничивать размер контекста и сохранять результат после ответа.

## 5. Конфигурируемые модель и провайдер

Настройки можно вынести из кода в `app/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Setting(BaseSettings):
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://models.github.ai/inference/"
    AI_MODEL: str = "openai/gpt-4o"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
```

Клиент и запрос тогда выглядят так:

```python
from openai import AsyncOpenAI

from app.core.config import settings

client = AsyncOpenAI(
    api_key=settings.AI_API_KEY,
    base_url=settings.AI_BASE_URL,
)

response = await client.chat.completions.create(
    model=settings.AI_MODEL,
    messages=[{"role": "user", "content": prompt}],
)
```

Пример `.env` для GitHub Models:

```dotenv
AI_API_KEY=your_github_token
AI_BASE_URL=https://models.github.ai/inference/
AI_MODEL=openai/gpt-4o
```

Для другого OpenAI-compatible провайдера обычно меняются `AI_API_KEY`, `AI_BASE_URL` и `AI_MODEL`. Совместимость конкретных параметров нужно проверять по документации провайдера.

## 6. Минимальная обработка timeout и ошибок

В текущем коде timeout и специализированная обработка ошибок не заданы. В расширенной реализации можно использовать:

```python
from openai import APIConnectionError, APIStatusError, APITimeoutError


async def get_chat_response(prompt: str) -> str:
    try:
        response = await client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=30.0,
        )
    except APITimeoutError as error:
        raise RuntimeError("AI provider timeout") from error
    except APIConnectionError as error:
        raise RuntimeError("AI provider is unavailable") from error
    except APIStatusError as error:
        raise RuntimeError(f"AI provider returned HTTP {error.status_code}") from error

    return response.choices[0].message.content or ""
```

Для production-сценария ошибки лучше преобразовывать в стабильные HTTP-ответы FastAPI, не показывая пользователю внутренние детали и токены.

## 7. Потоковая генерация ответа

Текущий проект возвращает ответ целиком. OpenAI-совместимый SDK поддерживает потоковый режим у провайдеров, которые его реализуют:

```python
stream = await client.chat.completions.create(
    model=settings.AI_MODEL,
    messages=[{"role": "user", "content": prompt}],
    stream=True,
)

async for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        yield delta
```

Для доставки этих фрагментов в браузер потребуется изменить API-эндпоинт и добавить SSE или WebSocket. Один только параметр `stream=True` не делает текущий `/api/chat` потоковым автоматически.

## 8. Пример простого мультиагентного сценария

Ниже — демонстрация последовательной оркестрации двух ролей без подключения дополнительного фреймворка. Она показывает принцип, но не является частью текущего приложения:

```python
async def ask_agent(instruction: str, task: str) -> str:
    response = await client.chat.completions.create(
        model=settings.AI_MODEL,
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": task},
        ],
    )
    return response.choices[0].message.content or ""


async def run_review_workflow(code: str) -> str:
    analysis = await ask_agent(
        "Ты агент-аналитик. Найди потенциальные проблемы в коде.",
        code,
    )
    review = await ask_agent(
        "Ты агент-проверяющий. Сформулируй итоговый отчёт на основе анализа.",
        analysis,
    )
    return review
```

Недостающие для production элементы: лимиты, timeout, трассировка, хранение промежуточных результатов, контроль стоимости и обработка отказа одного из агентов.

## 9. Параллельный запуск специализированных агентов

Если задачи независимы, их можно выполнять асинхронно:

```python
import asyncio


async def run_multiagent_task(task: str) -> dict[str, str]:
    results = await asyncio.gather(
        ask_agent("Ты эксперт по архитектуре.", task),
        ask_agent("Ты эксперт по безопасности.", task),
        ask_agent("Ты эксперт по тестированию.", task),
    )
    return {
        "architecture": results[0],
        "security": results[1],
        "testing": results[2],
    }
```

Параллельность сокращает время ожидания, но увеличивает число одновременных запросов к провайдеру. Перед применением нужны semaphore/rate limit, обработка частичных результатов и объединяющий агент или функция.

## 10. Поддержка локальной модели через OpenAI-compatible endpoint

Если локальный сервер предоставляет совместимый API, клиент может выглядеть так:

```python
from openai import AsyncOpenAI

local_client = AsyncOpenAI(
    api_key="local-key",
    base_url="http://localhost:11434/v1",
)

response = await local_client.chat.completions.create(
    model="local-model-name",
    messages=[{"role": "user", "content": "Привет"}],
)
```

Этот пример требует уже запущенного локального сервера и корректного имени модели. Текущая конфигурация проекта не переключается на него автоматически.

## 11. Рекомендуемый порядок развития

1. Вынести API key, base URL и модель в настройки.
2. Разделить `system` и `user` messages.
3. Добавить timeout, обработку ошибок, retry с ограничением.
4. Создать сущности беседы и сообщений в БД.
5. Добавить streaming через SSE или WebSocket.
6. Исправить безопасный вывод текста в браузере вместо небезопасного `innerHTML`.
7. Добавить тесты сервиса с mock-клиентом.
8. После этого реализовать оркестратор мультиагентных задач.
