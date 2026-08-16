# 08 — Отчёт по работе приложения с AI-моделями

## Содержание

1. [Обзор AI-интеграции](#1-обзор-ai-интеграции)
2. [Примеры кода, работающего с AI](#2-примеры-кода-работающего-с-ai)
3. [Возможности приложения](#3-возможности-приложения)
4. [Мультиагентное использование](#4-мультиагентное-использование)
5. [Формат общения с нейросетями](#5-формат-общения-с-нейросетями)
6. [Модели и провайдеры](#6-модели-и-провайдеры)

---

## 1. Обзор AI-интеграции

Приложение интегрируется с LLM через **GitHub Models API** (`https://models.github.ai/inference/`). Интеграция построена на официальном `openai` SDK (класс `AsyncOpenAI`), что означает полную совместимость с OpenAI-протоколом — но запросы идут на инфраструктуру GitHub, а не OpenAI.

| Параметр | Значение |
|---|---|
| **SDK** | `openai` (Python), `AsyncOpenAI` — асинхронный клиент |
| **Провайдер inference** | GitHub Models (`https://models.github.ai/inference/`) |
| **Модель по умолчанию** | `openai/gpt-4o` |
| **Аутентификация** | Bearer-токен (`GITHUB_TOKEN`) из `.env` |
| **Протокол** | HTTP/1.1, OpenAI Chat Completions API |
| **Режим** | Stateless — каждый запрос независим, без истории диалога |
| **Таймаут / retry** | Отсутствуют (см. раздел «Ограничения») |

---

## 2. Примеры кода, работающего с AI

Вся интеграция с AI сосредоточена в **двух файлах**: сервисном слое и API-эндпоинте.

### 2.1. Инициализация клиента — `app/services/chat.py:1–8`

Клиент создаётся как модульный синглтон при импорте. `AsyncOpenAI` направляется на GitHub Models через `base_url`, аутентификация — через `GITHUB_TOKEN`.

```python
from openai import AsyncOpenAI

from app.core.config import settings

client = AsyncOpenAI(
    api_key=settings.GITHUB_TOKEN,
    base_url="https://models.github.ai/inference/",
)
```

### 2.2. Вызов модели — `app/services/chat.py:11–23`

Функция `get_chat_response()` — единственная точка взаимодействия с LLM. Она формирует промпт, отправляет запрос и возвращает текст ответа.

```python
async def get_chat_response(prompt: str) -> str:
    """
    Asynchronously get a chat response from the OpenAI API.
    """
    message = (
        "Hey ChatGPT, you are a AI chatbot don not tell your name or any personal information. "
        "Here is the prompt you asked for: " + prompt
    )
    response = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": message}],
    )
    return response.choices[0].message.content.strip() if response.choices else ""
```

Ключевые моменты:
- **Системный промпт жёстко задан** в строке — пользователь не может его изменить.
- **История диалога не пере��аётся** — `messages` содержит ровно одно сообщение (роль `user`).
- **Модель захардкожена** — `openai/gpt-4o` указана строкой, без возможности переключения через конфиг.

### 2.3. API-эндпоинт — `app/api/v1/chat.py:12–17`

Эндпоинт `POST /api/chat` — единственный маршрут, через который проходит AI-запрос. Он валидирует тело, проверяет аутентификацию и делегирует в сервис.

```python
@router.post("/chat")
async def chat_endpoint(prompt: ChatRequest = Body(...), user: User = Depends(current_user)):
    """
    Chat API endpoint for chatting with the bot.
    """
    response = await get_chat_response(prompt=prompt.prompt)
    return {"response": response}
```

### 2.4. DTO для запроса — `app/schemas/chat.py:1–5`

Входные данные валидируются Pydantic: принимается единственное поле `prompt` (строка, без ограничений длины).

```python
from pydantic import BaseModel

class ChatRequest(BaseModel):
    prompt: str
```

### 2.5. Клиентский JS — `app/templates/index.html:186–208`

Фронтенд отправляет запрос через `fetch`, показывает индикатор «печатает», принимает ответ и рендерит его в чат.

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

const data = await response.json();
removeTypingIndicator();
addMessage(data.response || 'I received your message!', 'ai');
```

---

## 3. Возможности приложения

### Что работает сейчас

| Возможность | Статус | Реализация |
|---|---|---|
| Текстовый чат «один запрос — один ответ» | ✅ Работает | `POST /api/chat` → `get_chat_response()` |
| Аутентификация (JWT + Cookie) | ✅ Работает | FastAPI-Users, `fastapiusersauth` cookie |
| Регистрация / вход / выход | ✅ Работает | `/auth/register`, `/auth/login`, `/auth/logout` |
| Защита чата от неаутентифицированных | ✅ Работает | `Depends(current_user)` на эндпоинте и HTML-роуте |
| Индикатор набора текста | ✅ Работает | CSS-анимация `typing-dots` в `index.html` |
| Авто-resize поля ввода | ✅ Работает | JS в `index.html:166–169` |
| Отправка по Enter (с Shift для перевода строки) | ✅ Работает | JS в `index.html:269–274` |

### Чего нет

| Возможность | Статус | Комментарий |
|---|---|---|
| История диалога / контекст | ❌ Нет | Каждый запрос независим, `messages` — ровно одно сообщение |
| Сохранение сообщений в БД | ❌ Нет | Нет таблицы `message`, нет ORM-модели |
| Потоковая выдача (streaming) | ❌ Нет | Нет SSE / WebSocket; клиент ждёт полный ответ |
| Выбор модели пользователем | ❌ Нет | `model` захардкожен в `chat.py:20` |
| Загрузка изображений / файлов | ❌ Нет | Схема принимает только `prompt: str` |
| Системный промпт, настраиваемый пользователем | ❌ Нет | Промпт зашит в коде `chat.py:15–18` |
| Таймаут на вызов LLM | ❌ Нет | `AsyncOpenAI` создан без `timeout=...` |
| Retry / fallback при ошибке | ❌ Нет | Ошибка LLM → HTTP 500, на фронтенде — «Sorry, I encountered an error» |
| Rate limiting | ❌ Нет | Нет middleware |
| Векторный поиск / RAG | ❌ Нет | Нет эмбеддингов, нет векторной БД |

---

## 4. Мультиагентное использование

### Текущее состояние: **не поддерживается**

В текущей реализации мультиагентность отсутствует на всех уровнях:

1. **Один вызов модели на запрос.** `get_chat_response()` делает ровно один `client.chat.completions.create()` — нет цепочек вызовов, нет оркестрации нескольких моделей.
2. **Нет абстракции агента.** Нет классов/функций, инкапсулирующих «агента» с ролями, инструментами, памятью.
3. **Нет инструментов (function calling / tool use).** Параметр `tools` не передаётся в `chat.completions.create()`.
4. **Нет памяти.** `messages` всегда содержит одно сообщение — агент не помнит предыдущие ходы.
5. **Нет оркестратора.** Нет логики вида «модель A → ответ → модель B → финальный ответ».

### Что нужно для мультиагентности

Ниже — дорожная карта, основанная на текущей архитектуре. Каждый пункт — инкрементальное изменение.

#### Уровень 1: Несколько моделей с переключением

Минимальный шаг — вынести модель и `base_url` в конфигурацию и позволить выбирать модель per-request.

```python
# app/core/config.py — добавить
LLM_MODEL: str = "openai/gpt-4o"
LLM_BASE_URL: str = "https://models.github.ai/inference/"

# app/services/chat.py — параметризовать
async def get_chat_response(prompt: str, model: str = settings.LLM_MODEL) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    ...
```

Это уже даёт «мульти-модельность» — но не «мультиагентность».

#### Уровень 2: Цепочки вызовов (Sequential Agents)

Последовательная передача результата одной модели в следующую. Реализуется через простую функцию-оркестратор в сервисном слое:

```python
async def multi_agent_pipeline(prompt: str) -> str:
    # Агент 1: планировщик
    plan = await get_chat_response(prompt, model="openai/gpt-4o")

    # Агент 2: исполнитель
    result = await get_chat_response(plan, model="meta/llama-3.1-70b-instruct")

    # Агент 3: рецензент
    review = await get_chat_response(result, model="mistral/mistral-large")
    return review
```

Базовые строительные блоки для этого в проекте уже есть (`AsyncOpenAI` + `chat.completions.create`), но отсутствуют:
- передача контекста между шагами (нужен список `messages`),
- обработка ошибок и таймаутов на каждом шаге,
- логирование/трассировка цепочки.

#### Уровень 3: Полноценные агенты с инструментами

Для function calling и агентских циклов (reAct-паттерн) требуется:
- передавать `tools=[...]` в `chat.completions.create()`,
- реализовать цикл «модель → вызов инструмента → результат → модель»,
- для локальных инструментов (поиск в БД, HTTP-запросы) — асинхронные функции-обработчики.

В текущем стеке `openai` SDK поддерживает tool calling через параметр `tools` и `tool_choice`, но в коде приложения это не используется.

#### Уровень 4: Оркестрация через фреймворк

Для продвинутой мультиагентности (роутинг, делегирование, конкуренция агентов) обычно подключают один из:
- **OpenAI Agents SDK** — нативная интеграция с `openai` SDK,
- **LangGraph** — графы агентов с состоянием,
- **CrewAI** — ролевые агенты с задачами,
- **AutoGen** (Microsoft) — диалоговые мультиагентные системы.

Любой из них совместим с `AsyncOpenAI`, но это — существенное архитектурное расширение, выходящее за рамки текущего монолита.

### Вывод по мультиагентности

> Текущая архитектура **не поддерживает** мультиагентное использование. Однако базовый интеграционный слой (`AsyncOpenAI` → `chat.completions.create`) совместим с расширением до мультиагентности: достаточно добавить передачу истории сообщений, параметризацию модели и оркестратор в сервисном слое. Полноценная агентная система потребует引入 внешнего фреймворка.

---

## 5. Формат общения с нейросетями

### Протокол

Общение происходит через **OpenAI Chat Completions API** — стандартный JSON-over-HTTP протокол, который GitHub Models реализует как совместимый endpoint.

```
POST https://models.github.ai/inference/chat/completions
Authorization: Bearer <GITHUB_TOKEN>
Content-Type: application/json

{
  "model": "openai/gpt-4o",
  "messages": [
    {"role": "user", "content": "..."}
  ]
}
```

### Формат запроса (`messages`)

OpenAI Chat API использует список сообщений с ролями. Допустимые роли:

| Роль | Назначение | Используется в приложении? |
|---|---|---|
| `system` | Системный промпт — задаёт поведение модели | ❌ Не используется как отдельное сообщение; встроен в `user`-сообщение |
| `user` | Сообщение от пользователя | ✅ Единственная роль в текущем коде |
| `assistant` | Ответ модели (для передачи истории) | ❌ Нет — история не сохраняется |
| `tool` | Результат вызова инструмента | ❌ Нет — tools не используются |

В текущей реализации `messages` всегда содержит **ровно один** элемент:

```python
messages=[{"role": "user", "content": message}]
```

где `message` — конкатенация системного промпта и пользовательского ввода. Это нестандартный приём: вместо отдельного `system`-сообщения системная инструкция «склеена» в `user`-сообщение. Это снижает качество следования инструкции (модели лучше следуют `system`-роли) и создаёт поверхность для prompt injection — пользовательский текст идёт в том же сообщении, что и инструкция.

### Формат ответа

Модель возвращает объект `ChatCompletion`:

```python
response = await client.chat.completions.create(...)

# Структура ответа (OpenAI-совместимая):
response.id            # str — ID завершения
response.model         # str — фактически использованная модель
response.choices       # list[Choice]
response.choices[0].message.role     # "assistant"
response.choices[0].message.content  # str — текст ответа
response.usage          # CompletionUsage — токены (prompt/completion/total)
```

Приложение извлекает только текст:

```python
return response.choices[0].message.content.strip() if response.choices else ""
```

`response.usage` (счётчик токенов), `response.model` и метаданные игнорируются.

### Потоковость (streaming)

Не используется. Запрос отправляется без `stream=True`, клиент ждёт полного ответа. На фронтенде это маскируется индикатором «печатает», но для длинных ответов задержка может составить десятки секунд без обратной связи.

### Передача контекста

**Отсутствует.** Каждый `POST /api/chat` — независимый. Модель не «помнит» ни приветствие, ни предыдущие вопросы, ни свои ответы. Для полноценного диалога нужно:
1. сохранять сообщения в БД (таблица `message` с FK на `user`),
2. при запросе загружать последние N сообщений,
3. передавать их как `messages=[{system}, {user}, {assistant}, {user}, ...]`.

---

## 6. Модели и провайдеры

### Текущий провайдер: GitHub Models

Приложение использует **GitHub Models** — сервис inference от GitHub, доступный по токену `GITHUB_TOKEN`. Endpoint `https://models.github.ai/inference/` реализует OpenAI-совместимый протокол, поэтому запросы идут через стандартный `openai` SDK.

**Преимущества GitHub Models:**
- один токен (`GITHUB_TOKEN`) для всех моделей,
- бесплатный tier для публичных репозиториев / GitHub-аккаунтов,
- единый OpenAI-совместимый API для разных провайдеров моделей.

**Ограничения:**
- rate limits зависят от аккаунта GitHub,
- не все модели OpenAI API доступны (зависит от каталога GitHub Models),
- `base_url` захардкожен — нельзя переключить на другой провайдер без правки кода.

### Каталог моделей GitHub Models

GitHub Models предоставляет доступ к моделям разных семейств. Имена моделей имеют формат `<provider>/<model>`. Ниже — основные семейства (доступность зависит от текущего каталога GitHub Models):

| Семейство | Примеры моделей | Префикс |
|---|---|---|
| OpenAI | `openai/gpt-4o`, `openai/gpt-4o-mini`, `openai/o3-mini` | `openai/` |
| Meta Llama | `meta/llama-3.1-405b-instruct`, `meta/llama-3.1-70b-instruct`, `meta/llama-3.1-8b-instruct` | `meta/` |
| Mistral | `mistral/mistral-large`, `mistral/mistral-small`, `mistral/mistral-nemo` | `mistral/` |
| Microsoft Phi | `microsoft/phi-3-medium`, `microsoft/phi-3-small`, `microsoft/phi-4` | `microsoft/` |
| Google Gemini | `google/gemini-1.5-pro`, `google/gemini-1.5-flash` | `google/` |
| Cohere | `cohere/command-r`, `cohere/command-r-plus` | `cohere/` |
| AI21 | `ai21/jamba-1.5-large` | `ai21/` |

> Полный актуальный список моделей — на [GitHub Models](https://models.github.ai/catalog). Состав каталога меняется.

### Текущая конфигурация

В коде жёстко заданы:

```python
# app/services/chat.py
base_url = "https://models.github.ai/inference/"   # строка 7
model    = "openai/gpt-4o"                           # строка 20
api_key  = settings.GITHUB_TOKEN                     # из .env, строка 6
```

Переключение модели сейчас требует правки исходного кода.

### Подключение других провайдеров

Поскольку используется `openai` SDK с параметризуемым `base_url`, архитектура допускает подключение любого OpenAI-совместимого провайдера. Для этого нужно вынести `base_url` и `api_key` в конфигурацию:

```python
# app/core/config.py
GITHUB_TOKEN: str = ""                              # для GitHub Models
LLM_BASE_URL: str = "https://models.github.ai/inference/"
LLM_API_KEY: str = ""                               # отдельный ключ (fallback на GITHUB_TOKEN)
LLM_MODEL: str = "openai/gpt-4o"

# app/services/chat.py
client = AsyncOpenAI(
    api_key=settings.LLM_API_KEY or settings.GITHUB_TOKEN,
    base_url=settings.LLM_BASE_URL,
)
```

#### Совместимые провайдеры (OpenAI-протокол)

| Провайдер | `base_url` | Ключ |
|---|---|---|
| OpenAI (напрямую) | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| Azure OpenAI | `https://<resource>.openai.azure.com/openai/deployments/<deployment>` | ключ Azure |
| GitHub Models (текущий) | `https://models.github.ai/inference/` | `GITHUB_TOKEN` |
| Groq | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` |
| Together AI | `https://api.together.xyz/v1` | `TOGETHER_API_KEY` |
| OpenRouter | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| Локальный Ollama | `http://localhost:11434/v1` | любой (не проверяется) |
| vLLM (self-hosted) | `http://localhost:8000/v1` | зависит от конфигурации |

Переключение на любого из них — смена `base_url` + `api_key` в `.env`, без правки логики вызова (поскольку `chat.completions.create` — стандартный интерфейс).

### Рекомендации по расширению

1. **Вынести `model`, `base_url`, `api_key` в `config.py`** — позволит переключать модель и провайдера через `.env` без деплоя новой версии.
2. **Добавить `timeout` в `AsyncOpenAI(...)`** — сейчас при зависании inference-провайдера запрос висит бесконечно.
3. **Обернуть вызов LLM в `try/except`** — возвращать HTTP 502/503 вместо 500, с понятным сообщением.
4. **Логировать `response.usage`** — для контроля расхода токенов и стоимости.
5. **Для мультиагентности** — добавить передачу истории `messages` и параметр `tools` (см. раздел 4).

---

## Приложение: полный путь запроса к AI

```
Пользователь вводит текст в index.html
  │
  │  fetch('/api/chat', { body: { prompt: "Hello" } })
  ▼
app/api/v1/chat.py:12  chat_endpoint()
  │  1. Валидация: ChatRequest(prompt="Hello")
  │  2. Аутентификация: Depends(current_user) → JWT из cookie → User из БД
  ▼
app/services/chat.py:11  get_chat_response(prompt="Hello")
  │  3. Формирование сообщения:
  │     "Hey ChatGPT, you are a AI chatbot ... Here is the prompt you asked for: Hello"
  │  4. client.chat.completions.create(model="openai/gpt-4o", messages=[...])
  │
  │  ── HTTP POST ──────────────────────────────────────────────►
  │     https://models.github.ai/inference/chat/completions
  │     Authorization: Bearer <GITHUB_TOKEN>
  │     {"model": "openai/gpt-4o", "messages": [{"role": "user", "content": "..."}]}
  │  ◀──────────────────────────────────────────────────────────
  │     {"choices": [{"message": {"role": "assistant", "content": "Hi!"}}], ...}
  │
  │  5. response.choices[0].message.content.strip() → "Hi!"
  ▼
app/api/v1/chat.py:17  return {"response": "Hi!"}
  │
  │  HTTP 200 + JSON → браузер
  ▼
index.html:204  addMessage("Hi!", 'ai') → отрисовка пузыря чата
```

---

*Документ описывает состояние кода на момент последнего анализа. Для актуального списка моделей GitHub Models обращайтесь к [models.github.ai/catalog](https://models.github.ai/catalog).*