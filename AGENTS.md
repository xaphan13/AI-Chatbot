# AGENTS.md — AI Coding Agent Guide

> Universal instructions for AI coding agents (Claude Code, Aider, OpenCode, Cursor, Codex, etc.). If you are an AI agent, read this file first, then read the `docs/` directory — it is the single source of truth about the project.

## Project Overview

**AI Chatbot Assistant** — a full-stack AI chatbot web application.

- **Backend**: FastAPI (async), FastAPI-Users (JWT + Cookie auth), SQLAlchemy 2.0 (async), SQLite via `aiosqlite`, Alembic migrations.
- **AI Inference**: GitHub Models API (`https://models.github.ai/inference/`) accessed through the `openai` SDK (`AsyncOpenAI`), model: `openai/gpt-4o`.
- **Frontend**: Server-side rendering with Jinja2 templates + Tailwind CSS (CDN) + vanilla JavaScript.
- **Python**: 3.13. Package manager: `uv`.
- **Architecture**: Monolithic layered SSR application. No tests, no CI/CD yet.

## Quick Start (for AI agents)

**Do NOT do a full project walkthrough.** Read the `docs/` directory first — it contains an up-to-date architectural map:

| File | Purpose |
|------|---------|
| `docs/01_project_structure.md` | Project map: directory tree, per-file responsibilities, external dependencies |
| `docs/02_architecture.md` | Architecture, design patterns, data flow, config/state management |
| `docs/03_execution_flow.md` | App lifecycle, business processes, routing, error handling |
| `docs/04_code_quality.md` | Quality assessment, known code smells, security issues, bottlenecks |
| `docs/05_optimization_roadmap.md` | Roadmap: P0–P3 improvements, refactoring plan, DX recommendations |

## Project Structure

```
├── app/
│   ├── main.py              # App entry point: FastAPI app, HTML routes, router mounting
│   ├── api/v1/              # API routers: chat.py (POST /api/chat), users.py (FastAPIUsers config)
│   ├── core/                # config.py (Pydantic Settings), templates.py (unused duplicate)
│   ├── db/                  # base.py (DeclarativeBase), session.py (async engine + get_db)
│   ├── models/              # users.py — ORM User model
│   ├── schemas/             # Pydantic DTOs: chat.py (ChatRequest), users.py (UserRead/UserCreate/UserUpdate)
│   ├── services/            # chat.py (LLM client), user_manager.py (FastAPIUsers UserManager)
│   └── templates/           # landing.html, login.html, signup.html, index.html (chat UI)
├── alembic/                 # Migrations (versions/5770fda647a5_create_tables.py)
├── docs/                    # ← SINGLE SOURCE OF TRUTH (see table above)
├── pyproject.toml           # Dependencies, ruff/black config
└── alembic.ini              # Alembic config
```

## Build / Run / Test Commands

```bash
# Install dependencies
uv sync

# Run migrations
uv run alembic upgrade head

# Run the app (dev)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Create a new migration
uv run alembic revision --autogenerate -m "<message>"

# Lint & format
uv run ruff check .
uv run ruff format .
uv run black .

# Tests
# NOTE: no test suite exists yet — see docs/05_optimization_roadmap.md
```

## Code Style & Conventions

- Python 3.13, async/await throughout (no sync DB/IO in request paths).
- SQLAlchemy 2.0 declarative style: `Mapped[...]`, `mapped_column`, `DeclarativeBase`.
- Pydantic v2 schemas as DTOs (`pydantic-settings` for config).
- Ruff lints with `line-length = 100`; Black formats with `line-length = 120` (they conflict — prefer Ruff format).
- Docstrings in English where present.
- Follow the existing layered structure: `api/v1/` (routers) → `services/` (business logic) → `models/` + `db/` (data).

## Critical Notes & Gotchas

- **`app/static/` directory does not exist** — `app/main.py:20` mounts `StaticFiles` on it and will raise `RuntimeError` on startup. Create the directory or guard the mount before running the app.
- **`GITHUB_TOKEN` is required** for chat to work; it is read from `.env` / environment via `app/core/config.py`.
- **`SECRET` has an insecure default** in `app/core/config.py:16` — always set it via `.env` for real deployments.
- **Chat is stateless**: each `POST /api/chat` call is independent; there is no message/conversation persistence.
- **LLM calls have no timeout and no error handling** in `app/services/chat.py` — errors propagate as HTTP 500.
- **Known security issues** (from `docs/04_code_quality.md`): prompt injection in `app/services/chat.py`, XSS via `innerHTML` in `app/templates/index.html:225`.
- **Jinja2Templates is instantiated twice**: `app/main.py:19` and `app/core/templates.py` (the latter is unused).
- **Alembic**: `alembic/env.py` replaces `sqlite+aiosqlite` → `sqlite` before running migrations (line 19).
- **`pyproject.toml` requires Python >=3.13** — do not downgrade syntax for older versions.

## When Making Changes

1. Read the relevant file(s) in `docs/` first (especially `docs/02_architecture.md` and `docs/03_execution_flow.md`).
2. Make minimal changes; preserve the existing layered structure.
3. If you change an interface (function signature, router path, schema), update all call sites.
4. If you add/remove database fields, generate an Alembic migration.
5. Update the relevant `docs/` file if the architecture or data flow changes.
