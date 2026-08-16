# 08 — Отчёт: работа приложения с AI-моделями

> Отчёт о том, как приложение интегрировано с LLM: код интеграции, возможности, формат общения с моделями, доступные модели и провайдеры, а также анализ перспектив мультиагентного использования. Дата составления: 2026-08-16.

---

## 1. Общая схема интеграции

Приложение общается с нейросетью через **OpenAI-совместимый HTTP API**. Используется официальный Python-SDK `openai` (класс `AsyncOpenAI`), но запросы отправляются не на серверы OpenAI, а на альтернативный базовый URL — inference-эндпоинт **GitHub Models** (`https://models.github.ai/inference/`).

Цепочка вызова:

```
Браузер (index.html, fetch)
  → POST /api/chat            (app/api/v1/chat.py, защищён аутентификацией)
    → get_chat_response()      (app/services/chat.py, AsyncOpenAI-клиент)
      → HTTPS POST .../inference/chat/completions (GitHub Models)
        → модель openai/gpt-4o
```

Токен для доступа (`GITHUB_TOKEN`) читается из `.env` через `pydantic-settings` (`app/core/config.py`).

---

## 2. Код, работающий с AI

### 2.1 LLM-клиент — `app/services/chat.py`

Единственный файл с логикой обращения к модели. Весь AI-слой приложения — 23 строки:

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
        "Hey ChatGPT, you are a AI chatbot don not tell your name or any personal information. Here is the prompt you asked for: "
        + prompt
    )
    response = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": message}],
    )
    return response.choices[0].message.content.strip() if response.choices else ""
```

Характеристики реализации:

- **Асинхронный клиент** (`AsyncOpenAI`) — не блокирует event loop FastAPI.
- **Модель захардкожена**: `openai/gpt-4o` (в GitHub Models модели именуются с префиксом провайдера).
- **Системный промпт подмешивается строковой конкатенацией** прямо в пользовательское сообщение вместо отдельного сообщения с `role: "system"` — это известная уязвимость к prompt injection (см. `docs/04_code_quality.md`).
- **Нет таймаута, ретраев и обработки ошибок** — любая ошибка SDK уходит клиенту как HTTP 500.
- **История диалога не передаётся** — каждый запрос содержит ровно одно сообщение.

### 2.2 API-эндпоинт — `app/api/v1/chat.py`

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

- Маршрут монтируется в `app/main.py` с префиксом `/api` → итоговый путь `POST /api/chat`.
- Доступ только для авторизованных пользователей (`Depends(current_user)` — JWT/Cookie от FastAPI-Users).

### 2.3 DTO запроса — `app/schemas/chat.py`

```python
from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
```

### 2.4 Конфигурация — `app/core/config.py`

```python
class Setting(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./sqlite.db"
    GITHUB_TOKEN: str = ""          # токен GitHub Models
    SECRET: str = "your-secret-key-change-this-in-production"
    DEBUG: bool = False
```

### 2.5 Фронтенд-вызов — `app/templates/index.html`

```javascript
const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: message })
});

if (response.status === 401) {
    window.location.href = '/login';
    return;
}
```

Пока ждёт ответ, UI показывает «typing indicator» (анимированные точки). Ответ вставляется в DOM через `innerHTML` — это известная XSS-уязвимость (`app/templates/index.html:224`, задокументирована в `docs/04_code_quality.md`).

---

## 3. Возможности приложения

| Возможность | Реализация | Статус |
|---|---|---|
| Регистрация и вход пользователей | FastAPI-Users (JWT + Cookie), маршруты `/auth/*`, `/users/*` | ✅ |
| Веб-чат с LLM | SSR-страница `/chat` + `POST /api/chat` | ✅ |
| Ответы генерирует `gpt-4o` | `app/services/chat.py` | ✅ |
| Health check | `GET /health` (требует авторизации) | ✅ |
| История диалога / несколько чатов | — | ❌ чат полностью stateless, сообщения нигде не сохраняются |
| Стриминг ответов (SSE) | — | ❌ ответ возвращается целиком одним JSON |
| Выбор модели в UI | — | ❌ модель захардкожена |
| Загрузка файлов / изображений | — | ❌ |
| Function calling / инструменты | — | ❌ |

Итог: это **одноходовый защищённый чат-бот** «вопрос → ответ» без памяти контекста.

---

## 4. Мультиагентное использование

**В текущем виде — нет.** Мультиагентность невозможна по архитектурным причинам:

1. **Один клиент на модуль** — `AsyncOpenAI` создаётся один раз на уровне модуля `app/services/chat.py`; нет реестра агентов с разными моделями/промптами.
2. **Нет состояния диалога** — в `messages` всегда одно сообщение; агентам нечего передавать друг другу.
3. **Нет системных ролей** — «личность» бота вшита конкатенацией в пользовательский текст, а не задана `role: "system"`; ролями агентов управлять невозможно.
4. **Нет оркестратора** — отсутствует слой, который запускал бы несколько моделей, передавал результаты между ними и агрегировал итог.
5. **Нет tool/function calling** — агенты не могут вызывать инструменты приложения.

Что минимально потребуется для мультиагентности:

- хранить историю сообщений (БД + поле `messages[]` в DTO вместо `prompt: str`);
- вынести конфиг агента (модель, системный промпт, температура) в отдельную сущность;
- ввести сервис-оркестратор, который вызывает `client.chat.completions.create` для разных агентов и передаёт вывод одного как вход другому (паттерны «эстафета», «диспетчер/исполнители»);
- при желании — `stream=True` для живого вывода и `tools=[...]` для вызова функций.

Инфраструктурно SDK `openai` это всё поддерживает, т.е. препятствие — в объёме кода, а не в используемой библиотеке.

---

## 5. В каком виде происходит общение с моделями

Общение идёт по протоколу **OpenAI Chat Completions** поверх HTTPS в формате JSON.

**Запрос** (что приложение фактически отправляет):

```json
{
  "model": "openai/gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": "Hey ChatGPT, you are a AI chatbot don not tell your name or any personal information. Here is the prompt you asked for: <текст пользователя>"
    }
  ]
}
```

**Ответ** (что приложение читает):

```json
{
  "choices": [
    { "message": { "role": "assistant", "content": "текст ответа модели" } }
  ]
}
```

Особенности:

- только текстовые сообщения, один раунд («one-shot»), без истории;
- без стриминга (`stream` не задан — по умолчанию `false`);
- без параметров `temperature`, `max_tokens` и т.п. — значения по умолчанию провайдера;
- без structured outputs, function calling и мультимодальности;
- транспорт асинхронный: `await client.chat.completions.create(...)` внутри async-эндпоинта FastAPI.

---

## 6. Модели и провайдеры

### 6.1 Сейчас в коде

- **Провайдер:** GitHub Models (маркетплейс моделей GitHub, OpenAI-совместимый эндпоинт `https://models.github.ai/inference/`).
- **Модель:** ровно одна — `openai/gpt-4o`.

### 6.2 ⚠️ Важно: GitHub Models отключён

На момент составления отчёта (2026-08-16) проверка вживую показала, что **чат в приложении не работает**:

```
$ curl -X POST https://models.github.ai/inference/chat/completions
HTTP 410 Gone
{"error":{"code":"github_models_retirement_brownout",
 "message":"GitHub Models is temporarily unavailable as part of a scheduled retirement brownout."}}
```

По [официальной документации GitHub](https://docs.github.com/en/github-models): **«GitHub Models has been retired. As of July 30, 2026, GitHub Models has been fully retired»** — playground, каталог моделей, inference API и BYOK больше недоступны. GitHub рекомендует для доступа к моделям перейти на **Azure AI Foundry**.

Это блокирующая проблема для приложения: любой запрос к `/api/chat` завершается ошибкой (HTTP 500, т.к. обработка ошибок отсутствует).

### 6.3 Какие модели были доступны через GitHub Models (пока сервис работал)

Каталог GitHub Models включал модели нескольких провайдеров, все в формате `<провайдер>/<модель>`:

- **OpenAI** — GPT-4o, GPT-4o mini, модели серии o1/o3 (использовалась в приложении: `openai/gpt-4o`);
- **Meta** — семейство Llama 3.x;
- **Mistral AI** — Mistral Large / Small / Nemo;
- **Cohere** — Command R / Command R+;
- **AI21 Labs** — Jamba;
- **Microsoft (Azure AI)** — семейство Phi-3 / Phi-4.

Доступ был бесплатным в рамках rate limits GitHub, по обычному `GITHUB_TOKEN`.

### 6.4 На что можно переключиться

Поскольку интеграция сделана через стандартный SDK `openai`, смена провайдера сводится к замене `base_url`, `api_key` и имени модели:

```python
# Пример: прямой API OpenAI
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)  # base_url по умолчанию

# Пример: OpenRouter (сотни моделей через один ключ)
client = AsyncOpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

# Пример: локальная модель через Ollama (OpenAI-совместимый режим)
client = AsyncOpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)
```

Варианты провайдеров с OpenAI-совместимыми API:

| Провайдер | base_url | Комментарий |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | «родной» API, модели `gpt-4o`, `gpt-4.1`, o-серия |
| Azure AI Foundry | выдаётся порталом Azure | официальная рекомендация GitHub после закрытия GitHub Models |
| OpenRouter | `https://openrouter.ai/api/v1` | один ключ к моделям Anthropic, Meta, Mistral, Google и др. |
| Together AI / Groq / Fireworks | свои OpenAI-совместимые URL | быстрые инференс-хостинги открытых моделей |
| Ollama / vLLM (локально) | `http://localhost:11434/v1` и т.п. | полностью локальный запуск без внешних ключей |

Для Anthropic (Claude) напрямую нужен либо их SDK (`anthropic`), либо OpenAI-совместимый шлюз (например, OpenRouter).

**Рекомендация:** вынести `base_url`, `api_key` и `model` из `app/services/chat.py` в `app/core/config.py` (настройки окружения), чтобы провайдер менялся без правки кода, — заодно это первый шаг к мультиагентности из раздела 4.

---

## 7. Краткие выводы

1. AI-интеграция предельно простая: один асинхронный клиент `openai` SDK, одна модель, один запрос-ответ без истории.
2. Общение с моделью — текстовый JSON по схеме OpenAI Chat Completions, один раунд, без стриминга и инструментов.
3. Мультиагентность сейчас невозможна: нет истории, ролей, реестра агентов и оркестрации; но SDK и архитектура FastAPI позволяют её добавить.
4. Единственный настроенный провайдер — GitHub Models — **официально отключён 30 июля 2026 года**, чат в приложении сейчас не отвечает (HTTP 410). Требуется миграция на другого провайдера (Azure AI Foundry, OpenAI, OpenRouter или локальный Ollama) — это вопрос замены трёх параметров клиента.
5. Перед миграцией стоит устранить известные проблемы: prompt injection в сборке промпта, отсутствие таймаутов/обработки ошибок и XSS через `innerHTML` (см. `docs/04_code_quality.md`).
