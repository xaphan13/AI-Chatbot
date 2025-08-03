# 🤖 AI Chatbot Assistant

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![GitHub Models](https://img.shields.io/badge/GitHub%20Models-AI%20Inference-purple.svg)](https://github.blog/ai-and-ml/llms/solving-the-inference-problem-for-open-source-ai-projects-with-github-models/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modern, full-stack AI chatbot application built with **FastAPI** and **React**, leveraging **GitHub Models** for free, open-source AI inference. Features a beautiful, responsive UI with real-time chat capabilities and secure user authentication.

## ✨ Features

- **🤖 AI-Powered Conversations** - Uses GitHub Models for free AI inference
- **🔐 Secure Authentication** - JWT-based auth with FastAPI-Users
- **🎨 Modern UI** - Beautiful glassmorphism design with Tailwind CSS
- **📱 Responsive Design** - Works perfectly on desktop and mobile
- **⚡ Real-time Chat** - Instant message updates with typing indicators
- **🔒 Protected Routes** - Secure chat access for authenticated users
- **🚀 GitHub Integration** - Zero-config setup with GitHub Personal Access Tokens

## 🏗️ Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for Python
- **FastAPI-Users** - Complete user management solution
- **SQLAlchemy** - SQL toolkit and ORM
- **SQLite** - Lightweight database (easily upgradeable to PostgreSQL)
- **GitHub Models API** - Free AI inference endpoint

### Frontend
- **HTML5/Tailwind CSS** - Modern, responsive styling
- **Lucide Icons** - Beautiful, consistent icons
- **Vanilla JavaScript** - Lightweight, fast interactions
- **Glassmorphism Design** - Modern UI trends

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- GitHub Personal Access Token (for AI inference)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-chatbot.git
   cd ai-chatbot
   ```

2. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Create .env file
   cp .env.example .env
   
   # Edit .env with your GitHub token
   GITHUB_TOKEN=your_github_personal_access_token_here
   ```

4. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start the application**
   ```bash
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access the application**
   - 🌐 **Main App**: http://localhost:8000
   - 📚 **API Docs**: http://localhost:8000/docs

## 🔧 GitHub Models Integration

This application uses **GitHub Models** for AI inference, providing free access to powerful AI models without requiring paid API keys.

### How It Works
- **Zero Configuration**: No need for OpenAI keys or paid services
- **GitHub Token**: Uses your existing GitHub Personal Access Token
- **OpenAI Compatible**: Works with existing OpenAI SDK patterns
- **Free Tier**: Available for all GitHub users and open-source projects

### Setup Instructions
1. Create a [GitHub Personal Access Token](https://github.com/settings/tokens)
2. Grant `models:read` permission
3. Add the token to your `.env` file: `GITHUB_TOKEN=your_token_here`

### API Usage
```python
# Example API call to GitHub Models
import requests

headers = {
    'Authorization': f'Bearer {GITHUB_TOKEN}',
    'Content-Type': 'application/json'
}

payload = {
    'model': 'gpt-4o',
    'messages': [
        {'role': 'user', 'content': 'Hello, AI!'}
    ]
}

response = requests.post(
    'https://models.github.ai/inference/chat/completions',
    headers=headers,
    json=payload
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
- **Message History**: View your conversation history
- **Responsive Design**: Works on all devices

### API Endpoints
- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication
- `POST /auth/logout` - User logout
- `POST /api/chat` - Send message to AI
- `GET /users/me` - Get current user info

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
ai-chatbot/
├── app/
│   ├── api/v1/          # API routes
│   ├── core/            # Core configuration
│   ├── db/              # Database setup
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   └── templates/       # HTML templates
├── alembic/             # Database migrations
├── static/              # Static files (CSS, JS, images)
└── tests/               # Test files
```

### Adding New Features
1. **Backend**: Add new routes in `app/api/v1/`
2. **Frontend**: Update templates in `app/templates/`
3. **Database**: Create new migrations with `alembic revision`
4. **Testing**: Add tests in `tests/`

### Environment Variables
```bash
# Required
GITHUB_TOKEN=your_github_personal_access_token
DATABASE_URL=sqlite:///./chatbot.db
SECRET_KEY=your_secret_key_for_jwt

# Optional
DEBUG=True
HOST=0.0.0.0
PORT=8000
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_chat.py
```

### Manual Testing
- **Frontend**: Test on different screen sizes
- **API**: Use Swagger docs at `/docs`
- **Authentication**: Test login/logout flow
- **AI**: Verify GitHub Models responses

## 📦 Deployment

### Docker Deployment
```bash
# Build image
docker build -t ai-chatbot .

# Run container
docker run -p 8000:8000 -e GITHUB_TOKEN=your_token ai-chatbot
```

### Railway Deployment
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

### Heroku Deployment
```bash
# Install Heroku CLI
heroku create your-ai-chatbot
heroku config:set GITHUB_TOKEN=your_token
git push heroku main
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contribution Steps
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests for new functionality
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **GitHub Models** for providing free AI inference
- **FastAPI** for the excellent web framework
- **Tailwind CSS** for the beautiful styling
- **Lucide Icons** for the consistent icon set
- **FastAPI-Users** for user management

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/ai-chatbot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ai-chatbot/discussions)
- **Email**: support@yourproject.com

---

⭐ **Star this repository** if you find it helpful!

Made with ❤️ by [Your Name](https://github.com/yourusername)