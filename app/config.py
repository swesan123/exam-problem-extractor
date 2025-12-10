"""Application configuration using pydantic-settings."""
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Required
    openai_api_key: str = Field(..., description="OpenAI API key")

    # Vector Database
    vector_db_path: Path = Field(
        default=Path("./vector_store/chroma_index"),
        description="Path to vector database storage",
    )
    vector_db_type: Literal["chroma", "faiss"] = Field(
        default="chroma",
        description="Vector database type",
    )
    embedding_model: str = Field(
        default="text-embedding-ada-002",
        description="OpenAI embedding model name",
    )

    # OpenAI Models
    ocr_model: str = Field(
        default="gpt-4o",
        description="OpenAI Vision model for OCR (supports vision: gpt-4o, gpt-4-turbo, gpt-4o-mini)",
    )
    generation_model: str = Field(
        default="gpt-4o",
        description="OpenAI model for question generation",
    )

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    log_level: str = Field(default="INFO", description="Logging level")

    # Limits
    max_file_size_mb: int = Field(default=10, description="Maximum file size in MB")
    max_retrieve_k: int = Field(
        default=100,
        ge=1,
        le=100,
        description="Maximum number of retrieval results",
    )
    request_timeout_sec: int = Field(
        default=60,
        description="Request timeout in seconds",
    )

    def __init__(self, **kwargs):
        """Initialize settings and validate required fields."""
        super().__init__(**kwargs)
        # Ensure vector_db_path is a Path object
        if isinstance(self.vector_db_path, str):
            self.vector_db_path = Path(self.vector_db_path)
        # Create vector store directory if it doesn't exist
        self.vector_db_path.parent.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()

