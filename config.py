import os


class Config:
    """Flask application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///chat_history.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # llama.cpp OpenAI-compatible API
    LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8080/v1")
    LLM_MODEL = os.environ.get("LLM_MODEL", "default-model")
