"""
Configuration module for the Jaldhaara AI/Data Service.
Environment-driven settings with validation and local .env file support.
"""

from functools import lru_cache
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for AI/Data Service."""

    SERVICE_NAME: str = "jaldhaara-ai-data-service"
    SERVICE_VERSION: str = "1.0.0"

    # Server binding
    AI_SERVICE_HOST: str = Field(default="0.0.0.0", description="Host IP to bind HTTP service")
    AI_SERVICE_PORT: int = Field(default=8000, description="Port to bind HTTP service")
    AI_SERVICE_ENV: Literal["development", "testing", "staging", "production"] = Field(
        default="development", description="Runtime environment"
    )

    # Document storage directory (relative or absolute)
    DOCUMENTS_STORAGE_PATH: str = Field(
        default="data/documents", description="Directory path where versioned PDFs are stored"
    )

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Minimum logging level"
    )

    # Future AI / NLP placeholders (no secrets stored)
    LLM_PROVIDER: str = Field(default="gemini", description="Configured LLM provider")
    EMBEDDING_PROVIDER: str = Field(default="gemini", description="Configured embedding provider")
    CHROMADB_HOST: str = Field(default="localhost", description="ChromaDB service host")
    CHROMADB_PORT: int = Field(default=8000, description="ChromaDB service port")
    CHROMADB_COLLECTION: str = Field(
        default="csr_documents", description="ChromaDB vector collection name"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("AI_SERVICE_PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, received {v}")
        return v


@lru_cache
def get_settings() -> Settings:
    """Returns cached singleton application settings."""
    return Settings()
