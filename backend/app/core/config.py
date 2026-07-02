import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # LLM provider: "ollama", "gemini", or "none"
    LLM_PROVIDER: str = "ollama"

    # Ollama chat model for local AI reasoning
    OLLAMA_MODEL: str = "qwen2.5:3b"

    # Gemini API key/model, used only when LLM_PROVIDER or EMBEDDING_PROVIDER is "gemini"
    GEMINI_API_KEY: str = ""

    # Gemini models. Keep these configurable because quota/model access can vary by key.
    GEMINI_CHAT_MODEL: str = "gemini-2.0-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"

    # Embedding provider: "local" keeps ingest offline; "gemini" uses Gemini embeddings.
    EMBEDDING_PROVIDER: str = "local"
    
    # Path where ChromaDB SQLite/index files will be stored
    CHROMA_DB_PATH: str = "./chroma_db"
    
    # FastAPI port
    PORT: int = 8000
    
    # Allow loading from a .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()
