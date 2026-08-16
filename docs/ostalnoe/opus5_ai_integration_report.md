# 08. Отчёт по работе приложения с моделями AI

> Дата составления: анализ текущего состояния кодовой базы `AI-Chatbot`.
> Отчёт описывает **то, что реально есть в коде**, и отдельно — то, что технически возможно добавить.

---

## 1. Краткое резюме

| Параметр | Значение |
|---|---|
| SDK для работы с LLM | `openai>=1.98.0` (`AsyncOpenAI`) |
| Провайдер | GitHub Models (`https://models.github.ai/inference/`) |
| Модель | `openai/gpt-4o` (жёстко зашита в коде) |
| Протокол | HTTPS, OpenAI-совместимый `POST /chat/completions` |
| Режим общения | Один запрос → один полный ответ (без стриминга) |
| Память диалога | **Отсутствует** — каждый запрос независим |
| Мультиагентность | **Отсутствует**, но архитектурно достижима (см. §6) |
| Аутентификация к API | GitHub PAT из переменной `GITHUB_TOKEN` |
| Обработка ошибок / таймауты | **Отсутствуют** |

Весь AI-функционал приложения умещается в **один файл на 23 строки** — `app/services/chat.py`. Это одноходовый stateless-чат: пользователь отправляет строку, получает строку.

---

## 2. Полный код, работающий с AI

### 2.1. Слой сервиса — `app/services/chat.py`

Это единственное место в проекте, где происходит обращение к нейросети.

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

Что здесь происходит по шагам:

1. **Клиент создаётся один раз при импорте модуля** — на уровне модуля, а не внутри функции. Это правильно с точки зрения переиспользования HTTP-пула соединений `httpx`, но означает, что клиент собирается на этапе старта приложения и токен нельзя поменять без перезапуска.
2. `base_url` переопределён на GitHub Models. Именно эта одна строка превращает клиент OpenAI в клиент стороннего провайдера — сам SDK остаётся неизменным.
3. **Системная инструкция склеивается с пользовательским вводом в одну строку** и отправляется с ролью `user`. Роль `system` не используется вообще.
4. Вызывается `chat.completions.create` — классический non-streaming запрос.
5. Из ответа берётся `choices[0].message.content`, обрезаются пробелы. Если `choices` пуст — возвращается пустая строка.

### 2.2. Слой API — `app/api/v1/chat.py`

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

Роутер монтируется в `app/main.py:23` с префиксом `/api`, итоговый путь — `POST /api/chat`. Эндпоинт защищён зависимостью `current_user`: без валидной сессии FastAPI-Users вернёт `401`.

### 2.3. Контракт запроса — `app/schemas/chat.py`

```python
from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
```

Одно поле, без ограничений длины, без валидации содержимого.

### 2.4. Конфигурация — `app/core/config.py`

```python
class Setting(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./sqlite.db"
    GITHUB_TOKEN: str = ""          # ← ключ доступа к моделям
    SECRET: str = "your-secret-key-change-this-in-production"
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )
```

Из всей AI-конфигурации наружу вынесен **только токен**. Модель, base_url, температура, лимит токенов — всё захардкожено или не задано вовсе.

### 2.5. Клиентская часть — `app/templates/index.html`

```javascript
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

// Remove typing indicator and add AI response
removeTypingIndicator();
addMessage(data.response || 'I received your message!', 'ai');
```

Куки сессии уходят автоматически (same-origin). Пока ждём ответ — показывается анимация «печатает». История сообщений живёт только в DOM и стирается при перезагрузке страницы.

---

## 3. Какие возможности предлагает приложение

### 3.1. Реально работающие

| Возможность | Где реализована | Комментарий |
|---|---|---|
| Одноходовый вопрос-ответ к LLM | `services/chat.py` | Ядро всего AI-функционала |
| Асинхронная обработка | `AsyncOpenAI` + FastAPI | Сервер не блокируется на время ответа модели |
| Ограничение доступа по аутентификации | `Depends(current_user)` | Анонимный пользователь получит 401 |
| Регистрация / вход / выход | FastAPI-Users, JWT + Cookie | `/auth/register`, `/auth/login`, `/auth/logout` |
| Веб-интерфейс чата | `templates/index.html` | Tailwind CDN + vanilla JS |
| Индикатор набора текста | JS-функция `showTypingIndicator()` | Косметика, компенсирует отсутствие стриминга |
| Мягкая деградация при ошибке сети | `try/catch` в JS | Показывает «Sorry, I encountered an error» |
| Health-check | `GET /health` | Требует аутентификации, что для health-check спорно |

### 3.2. Отсутствующие возможности

- **Нет истории диалога.** Модель не помнит ни одного предыдущего сообщения — ни в рамках сессии, ни между сессиями. В БД нет таблиц сообщений или чатов.
- **Нет стриминга.** Пользователь ждёт полный ответ; при длинных генерациях это десятки секунд «в тишине».
- **Нет выбора модели.** Ни в UI, ни в API, ни в конфиге.
- **Нет управления параметрами генерации** — `temperature`, `max_tokens`, `top_p` не передаются, используются значения провайдера по умолчанию.
- **Нет таймаутов и ретраев.** Зависший запрос к провайдеру держит соединение неограниченно долго.
- **Нет обработки ошибок на бэкенде.** Любое исключение SDK (401 от провайдера, 429 rate limit, сетевой сбой) вылетает в FastAPI и превращается в `500 Internal Server Error`.
- **Нет учёта токенов и стоимости.** Поле `response.usage` игнорируется.
- **Нет rate limiting** на стороне приложения — один пользователь может исчерпать общую квоту токена.
- **Нет функций / tool calling, RAG, загрузки файлов, работы с изображениями.**

### 3.3. Проблемы безопасности в AI-контуре

1. **Прямая инъекция в промпт** (`services/chat.py:15-18`). Инструкция и пользовательский ввод склеиваются в одну строку с ролью `user`. Ввод вида `Ignore all previous instructions and ...` полностью перехватывает поведение бота. Инструкция и так не имеет приоритета — её нужно как минимум перенести в отдельное сообщение с ролью `system`.
2. **XSS через ответ модели** (`templates/index.html:224`). Текст вставляется через `innerHTML` без экранирования. Ответ LLM, содержащий HTML или `<img onerror=...>`, выполнится в браузере пользователя. Лечится заменой на `textContent`.
3. **Отсутствие лимита длины `prompt`.** Схема `ChatRequest` не ограничивает поле — можно отправить мегабайтную строку и сжечь квоту.

---

## 4. В каком виде происходит общение с нейросетью

### 4.1. Транспорт и формат

Общение идёт по **OpenAI Chat Completions API** — HTTPS-запрос `POST` на `https://models.github.ai/inference/chat/completions` с заголовком `Authorization: Bearer <GITHUB_TOKEN>`. Тело запроса, которое фактически формирует SDK:

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

Ответ провайдера:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "openai/gpt-4o",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "текст ответа" },
      "finish_reason": "stop"
    }
  ],
  "usage": { "prompt_tokens": 42, "completion_tokens": 128, "total_tokens": 170 }
}
```

Приложение использует из этого ровно одно поле — `choices[0].message.content`. `usage` и `finish_reason` отбрасываются.

### 4.2. Полная цепочка одного сообщения

```
Браузер
  │  fetch POST /api/chat  { "prompt": "..." }  + cookie сессии
  ▼
FastAPI  app/main.py → router "/api"
  │  Depends(current_user) — проверка JWT-cookie (401 при провале)
  │  Pydantic-валидация ChatRequest
  ▼
app/api/v1/chat.py :: chat_endpoint
  │  await get_chat_response(prompt=...)
  ▼
app/services/chat.py :: get_chat_response
  │  склейка инструкции с промптом → одно сообщение role=user
  │  await client.chat.completions.create(...)
  ▼
HTTPS → https://models.github.ai/inference/chat/completions
  │  Authorization: Bearer $GITHUB_TOKEN
  ▼
GitHub Models → маршрутизация на openai/gpt-4o
  │  (ожидание полной генерации, без стриминга)
  ▼
обратно: content.strip()
  ▼
JSON  { "response": "..." }
  ▼
Браузер: removeTypingIndicator() → addMessage(data.response, 'ai')
```

Ключевая характеристика: **синхронный по смыслу цикл «запрос-ответ» без сохранения состояния**. Между двумя сообщениями пользователя нет никакой связи ни на бэкенде, ни на стороне провайдера.

---

## 5. Какие модели и провайдеры можно использовать

### 5.1. Текущий провайдер: GitHub Models

Приложение обращается к GitHub Models — витрине моделей, доступной по GitHub-токену и выставляющей OpenAI-совместимый API. Особенности:

- **Аутентификация**: персональный токен GitHub (PAT) с правом на чтение моделей. Тот же `GITHUB_TOKEN`, что и в `.env`.
- **Именование моделей**: формат `<издатель>/<модель>` — отсюда `openai/gpt-4o`, а не просто `gpt-4o`.
- **Каталог** включает модели разных издателей: OpenAI (GPT-4o, GPT-4o-mini, серия o), Meta (Llama), Mistral, Cohere, Microsoft (Phi), DeepSeek, xAI (Grok), AI21 и другие. Состав каталога меняется — актуальный список смотрите в GitHub Marketplace → Models.
- **Квоты**: на бесплатном уровне действуют ограничения по запросам в минуту/сутки и по размеру контекста. При превышении провайдер вернёт `429` — сейчас приложение превратит это в `500`.
- **Назначение**: GitHub позиционирует бесплатный уровень как площадку для прототипирования, не для продакшена. Для боевой нагрузки предполагается переход на Azure AI Inference с полноценным ключом.

### 5.2. Как переключить модель прямо сейчас

Минимальное изменение — одна строка в `app/services/chat.py`:

```python
response = await client.chat.completions.create(
    model="openai/gpt-4o-mini",   # было: openai/gpt-4o
    messages=[...],
)
```

Корректнее вынести в конфиг. Добавить в `app/core/config.py`:

```python
class Setting(BaseSettings):
    ...
    GITHUB_TOKEN: str = ""
    LLM_BASE_URL: str = "https://models.github.ai/inference/"
    LLM_MODEL: str = "openai/gpt-4o"
    LLM_TEMPERATURE: float = 0.7
    LLM_TIMEOUT: float = 60.0
```

И использовать в `app/services/chat.py`:

```python
client = AsyncOpenAI(
    api_key=settings.GITHUB_TOKEN,
    base_url=settings.LLM_BASE_URL,
    timeout=settings.LLM_TIMEOUT,
    max_retries=2,
)

response = await client.chat.completions.create(
    model=settings.LLM_MODEL,
    temperature=settings.LLM_TEMPERATURE,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ],
)
```

Это заодно закрывает проблему инъекции промпта (§3.3.1) и отсутствия таймаутов.

### 5.3. Другие провайдеры, доступные без смены SDK

Поскольку код использует стандартный `AsyncOpenAI`, любой провайдер с OpenAI-совместимым эндпоинтом подключается **сменой `base_url` и ключа** — трогать логику не нужно:

| Провайдер | `base_url` | Пример значения `model` |
|---|---|---|
| GitHub Models (текущий) | `https://models.github.ai/inference/` | `openai/gpt-4o` |
| OpenAI напрямую | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini` |
| Azure OpenAI | `https://<resource>.openai.azure.com/openai/v1/` | имя deployment'а |
| OpenRouter (агрегатор) | `https://openrouter.ai/api/v1` | `anthropic/claude-sonnet-4`, `google/gemini-2.5-pro` |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| Together AI | `https://api.together.xyz/v1` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat` |
| Mistral | `https://api.mistral.ai/v1` | `mistral-large-latest` |
| Ollama (локально) | `http://localhost:11434/v1` | `llama3.2`, `qwen2.5` |
| vLLM / LM Studio (локально) | `http://localhost:8000/v1` | зависит от загруженной модели |

Провайдеры **без** OpenAI-совместимости (Anthropic напрямую, Google Gemini через нативный SDK) потребуют отдельного клиента и адаптера — но и это укладывается в существующую структуру: достаточно спрятать различия за общим интерфейсом в слое `services/`.

---

## 6. Возможно ли мультиагентное использование

### 6.1. Текущее состояние — нет

В коде нет ничего от мультиагентности:

- одна функция, один вызов модели, одна роль;
- нет ролей, инструментов (tool calling), маршрутизации между агентами;
- нет состояния — а без общей памяти агенты не могут передавать друг другу контекст;
- нет оркестратора, очередей, фоновых задач.

### 6.2. Насколько архитектура к этому готова

Готова неплохо — по трём причинам:

1. **Асинхронность сквозная.** `AsyncOpenAI` + FastAPI позволяют запускать несколько вызовов модели параллельно через `asyncio.gather` без единой правки в транспортном слое.
2. **Слоистая структура.** Граница `api/v1/` → `services/` уже проведена. Оркестратор агентов — это новый модуль в `services/`, роутер о нём знать не обязан.
3. **SDK универсален.** Разным агентам можно назначить разные модели и даже разных провайдеров, создав несколько экземпляров клиента.

### 6.3. Что придётся добавить

| Блок | Зачем | Оценка сложности |
|---|---|---|
| Персистентность диалогов (таблицы `chats`, `messages` + миграция Alembic) | Без общей памяти агенты не смогут работать над одной задачей | Средняя |
| Абстракция агента (роль, системный промпт, модель, набор инструментов) | Ядро мультиагентности | Средняя |
| Оркестратор (последовательный / параллельный / маршрутизатор) | Управление порядком вызовов | Средняя |
| Tool calling (`tools=[...]`, обработка `tool_calls`) | Чтобы агенты могли что-то делать, а не только говорить | Высокая |
| Стриминг (SSE или WebSocket) | Многошаговые сценарии идут долго, пользователю нужен прогресс | Средняя |
| Бюджеты и лимиты (максимум шагов, потолок токенов) | Защита от бесконечных циклов между агентами | Низкая |
| Обработка ошибок и ретраи | Чем больше вызовов, тем выше шанс сбоя | Низкая |

### 6.4. Набросок минимального мультиагентного слоя

Так может выглядеть простой конвейер из нескольких ролей поверх существующего кода. Это **предложение, а не текущий код**:

```python
# app/services/agents.py  (файла в проекте пока нет)
import asyncio
from dataclasses import dataclass

from app.core.config import settings
from app.services.chat import client


@dataclass(frozen=True)
class Agent:
    name: str
    system_prompt: str
    model: str = settings.LLM_MODEL
    temperature: float = 0.7

    async def run(self, task: str) -> str:
        response = await client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": task},
            ],
        )
        return response.choices[0].message.content.strip() if response.choices else ""


RESEARCHER = Agent(
    name="researcher",
    system_prompt="Ты аналитик. Собери ключевые факты по задаче. Только факты, без выводов.",
)
CRITIC = Agent(
    name="critic",
    system_prompt="Ты критик. Найди слабые места и пробелы в предложенном материале.",
    temperature=0.3,
)
WRITER = Agent(
    name="writer",
    system_prompt="Ты редактор. Собери из материала и критики финальный связный ответ.",
)


async def run_pipeline(task: str) -> str:
    """Последовательный конвейер: исследование → критика → финальный текст."""
    facts = await RESEARCHER.run(task)
    critique = await CRITIC.run(f"Задача: {task}\n\nМатериал:\n{facts}")
    return await WRITER.run(
        f"Задача: {task}\n\nМатериал:\n{facts}\n\nКритика:\n{critique}"
    )


async def run_parallel(task: str, agents: list[Agent]) -> dict[str, str]:
    """Параллельный опрос нескольких агентов — все вызовы идут одновременно."""
    results = await asyncio.gather(*(agent.run(task) for agent in agents))
    return dict(zip((a.name for a in agents), results))
```

Подключение к API потребовало бы нового роутера рядом с существующим `POST /api/chat` — например, `POST /api/agents/pipeline`, — без изменения текущего эндпоинта.

**Важное предупреждение по стоимости.** Конвейер из трёх агентов — это три вызова модели на одно сообщение пользователя. На бесплатных квотах GitHub Models такой сценарий упрётся в rate limit почти сразу. Прежде чем строить мультиагентность, нужно реализовать таймауты, ретраи с backoff и учёт токенов из `response.usage`.

---

## 7. Приоритетные рекомендации по AI-слою

Порядок отражает соотношение «риск / трудозатраты».

**P0 — исправить немедленно (каждый пункт — несколько строк кода):**

1. Вынести системную инструкцию в сообщение с ролью `system`, перестать склеивать её с пользовательским вводом — `app/services/chat.py:15-18`.
2. Заменить `innerHTML` на `textContent` при выводе ответа модели — `app/templates/index.html:224`.
3. Добавить `timeout` и `max_retries` при создании `AsyncOpenAI`.
4. Обернуть вызов модели в `try/except` и возвращать осмысленный HTTP-статус вместо голого `500`.
5. Ограничить длину поля `prompt` в `ChatRequest` через `Field(max_length=...)`.

**P1 — ближайшие улучшения:**

6. Вынести `LLM_MODEL`, `LLM_BASE_URL`, `LLM_TEMPERATURE` в `app/core/config.py`.
7. Логировать `response.usage` для контроля расхода токенов.
8. Добавить rate limiting на `POST /api/chat` в разрезе пользователя.

**P2 — функциональное развитие:**

9. Сохранять историю диалога в БД и передавать её в `messages` — это превратит одноходовый бот в настоящий чат.
10. Внедрить стриминг (`stream=True` + SSE) для мгновенного отклика.
11. Дать пользователю выбор модели в UI.

**P3 — мультиагентность:** только после закрытия P0–P2, по плану из §6.3.

---

## 8. Связанные документы

- `docs/01_project_structure.md` — карта проекта и назначение файлов
- `docs/02_architecture.md` — слои, паттерны, поток данных
- `docs/03_execution_flow.md` — жизненный цикл приложения и маршрутизация
- `docs/04_code_quality.md` — общая оценка качества и проблемы безопасности
- `docs/05_optimization_roadmap.md` — общий роадмап P0–P3
- `docs/06_frontend_guide.md` — устройство фронтенда
