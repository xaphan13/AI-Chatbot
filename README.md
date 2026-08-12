# AI Chatbot Assistant

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com/)
[![GitHub Models](https://img.shields.io/badge/GitHub%20Models-AI%20Inference-purple.svg)](https://github.blog/ai-and-ml/llms/solving-the-inference-problem-for-open-source-ai-projects-with-github-models/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modern, full-stack AI chatbot application built with **FastAPI** and **Jinja2**, leveraging **GitHub Models** for free, open-source AI inference. Features a beautiful, responsive UI with real-time chat capabilities and secure user authentication.

## 📚 Documentation

The `docs/` directory is the **single source of truth** about the project:

| File | Purpose |
|------|---------|
| [`docs/01_project_structure.md`](docs/01_project_structure.md) | Project map: directory tree, per-file responsibilities, external dependencies |
| [`docs/02_architecture.md`](docs/02_architecture.md) | Architecture, design patterns, data flow, config/state management |
| [`docs/03_execution_flow.md`](docs/03_execution_flow.md) | App lifecycle, business processes, routing, error handling |
| [`docs/04_code_quality.md`](docs/04_code_quality.md) | Quality assessment, known code smells, security issues, bottlenecks |
| [`docs/05_optimization_roadmap.md`](docs/05_optimization_roadmap.md) | Roadmap: P0–P3 improvements, refactoring plan, DX recommendations |

**For AI coding agents**: see [`AGENTS.md`](AGENTS.md) (universal, all harnesses) or [`CLAUDE.md`](CLAUDE.md) (Claude Code) — both instruct agents to read `docs/` first, without walking the whole project.

## ✨ Features

- **🤖 AI-Powered Conversations** — Uses GitHub Models for free AI inference
- **🔐 Secure Authentication** — JWT-based auth with FastAPI-Users
- **🎨 Modern UI** — Beautiful glassmorphism design with Tailwind CSS
- **📱 Responsive Design** — Works perfectly on desktop and mobile
- **⚡ Real-time Chat** — Instant message updates with typing indicators
- **🔒 Protected Routes** — Secure chat access for authenticated users
- **🚀 GitHub Integration** — Zero-config setup with GitHub Personal Access Tokens

## 🏗️ Tech Stack

### Backend
- **FastAPI** — Modern, fast web framework for Python (async)
- **FastAPI-Users** — Complete user management solution (JWT + Cookie auth)
- **SQLAlchemy 2.0** — Async SQL toolkit and ORM
- **SQLite** — Lightweight database via `aiosqlite` (easily upgradeable to PostgreSQL)
- **Alembic** — Database migrations
- **GitHub Models API** — Free AI inference endpoint

### Frontend
- **Jinja2 Templates** — Server-side rendering
- **HTML5/Tailwind CSS** — Modern, responsive styling (CDN)
- **Lucide Icons** — Beautiful, consistent icons
- **Vanilla JavaScript** — Lightweight, fast interactions
- **Glassmorphism Design** — Modern UI trends

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager (recommended)
- GitHub Personal Access Token with `models:read` permission (for AI inference)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Sohail342/AI-Chatbot.git
   cd ai-chatbot
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   # Create .env file
   touch .env

   # Edit .env with your GitHub token and a secret
   GITHUB_TOKEN=your_github_personal_access_token
   SECRET=generate-a-random-secret-key-here
   ```

4. **Run database migrations**
   ```bash
   uv run alembic upgrade head
   ```

5. **Start the application**
   ```bash
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access the application**
   - 🌐 **Main App**: http://localhost:8000
   - 📚 **API Docs**: http://localhost:8000/docs

> **Note**: the app mounts `StaticFiles` on `app/static/` — create that directory first if it does not exist, otherwise startup fails.

## 🔧 GitHub Models Integration

This application uses **GitHub Models** for AI inference, providing free access to powerful AI models without requiring paid API keys.

### How It Works
- **Zero Configuration**: No need for OpenAI keys or paid services
- **GitHub Token**: Uses your existing GitHub Personal Access Token
- **OpenAI Compatible**: Works with existing OpenAI SDK patterns (`AsyncOpenAI` with a custom `base_url`)
- **Free Tier**: Available for all GitHub users and open-source projects

### Setup Instructions
1. Create a [GitHub Personal Access Token](https://github.com/settings/tokens)
2. Grant `models:read` permission
3. Add the token to your `.env` file: `GITHUB_TOKEN=your_token_here`

### API Usage
```python
# Example API call to GitHub Models
import requests

headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Content-Type": "application/json"}

payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": "Hello, AI!"}]}

response = requests.post(
    "https://models.github.ai/inference/chat/completions", headers=headers, json=payload
)
```

## 🎯 Usage Guide

### User Registration & Login
1. Visit http://localhost:8000
2. Click "Get Started" to register a new account
3. Login with your credentials
4. Access the AI chat interface

### Chat Features
- **Send Messages**: Type in the chat input and press Enter
- **Typing Indicators**: See when the AI is thinking
- **Responsive Design**: Works on all devices

### API Endpoints
- `POST /auth/register` — User registration
- `POST /auth/login` — User authentication
- `POST /auth/logout` — User logout
- `POST /api/chat` — Send message to AI
- `GET /users/me` — Get current user info
- `GET /chat` — Chat interface (HTML, requires auth)
- `GET /health` — Health check (requires auth)

## 🎨 Design Features

### Modern UI Elements
- **Glassmorphism Cards**: Semi-transparent, blurred backgrounds
- **Gradient Animations**: Dynamic color transitions
- **Floating Animations**: Subtle motion for engagement
- **Hover Effects**: Interactive feedback on all elements
- **Responsive Grid**: Adapts to any screen size

### Color Scheme
- **Primary**: Purple gradients (#667eea → #764ba2)
- **Secondary**: Pink accents (#ec4899)
- **Background**: Dark theme with glass effects
- **Text**: High contrast for readability

## 🛠️ Development

### Project Structure
```
├── app/
│   ├── main.py              # App entry point: FastAPI app, HTML routes, router mounting
│   ├── api/v1/              # API routers: chat.py, users.py (FastAPIUsers config)
│   ├── core/                # config.py (Pydantic Settings), templates.py
│   ├── db/                  # base.py, session.py (async engine + get_db)
│   ├── models/              # users.py — ORM User model
│   ├── schemas/             # Pydantic DTOs: chat.py, users.py
│   ├── services/            # chat.py (LLM client), user_manager.py
│   └── templates/           # landing.html, login.html, signup.html, index.html
├── alembic/                 # Database migrations
├── docs/                    # ← Single source of truth (see Documentation)
├── pyproject.toml           # Dependencies, ruff/black config
└── alembic.ini              # Alembic config
```

### Adding New Features
1. **Backend**: Add new routes in `app/api/v1/`
2. **Frontend**: Update templates in `app/templates/`
3. **Database**: Create new migrations with `uv run alembic revision --autogenerate -m "<message>"`
4. **Documentation**: Update the relevant file in `docs/` if architecture or data flow changes

### Environment Variables
```bash
# Required
GITHUB_TOKEN=your_github_personal_access_token
SECRET=your_secret_key_for_jwt

# Database (optional, default: sqlite+aiosqlite:///./sqlite.db)
DATABASE_URL=sqlite+aiosqlite:///./chatbot.db

# Optional
DEBUG=False
```

### Lint & Format
```bash
uv run ruff check .
uv run ruff format .
uv run black .
```

## 🧪 Testing

> **Status**: no automated test suite exists yet. Setting up tests is part of the roadmap — see `docs/05_optimization_roadmap.md`.

### Manual Testing
- **Frontend**: Test on different screen sizes
- **API**: Use Swagger docs at `/docs`
- **Authentication**: Test login/logout flow
- **AI**: Verify GitHub Models responses

## 📝 License

MIT

