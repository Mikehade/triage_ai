from __future__ import annotations
from pathlib import Path
from functools import lru_cache
from pydantic import Field
from typing import Optional, List, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # ── App ───────────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    DEBUG: Optional[bool] = Field(default=False, validation_alias="API_ROOT_PATH")

    API_V_STR: str = "/api/v1"
    VERSION: str = "1.0.0"

    # ── Database ──────────────────────────────────────────────────────────────
    PG_PORT: Optional[str] = Field(..., validation_alias="PG_PORT")
    PG_DB_NAME: Optional[str] = Field(..., validation_alias="PG_DB_NAME")
    PG_PASSWORD: Optional[str] = Field(..., validation_alias="PG_PASSWORD")
    PG_HOSTNAME: Optional[str] = Field(..., validation_alias="PG_HOSTNAME")
    PG_USERNAME: Optional[str] = Field(..., validation_alias="PG_USERNAME")

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_DB: Optional[str] = Field(..., validation_alias="REDIS_DB")
    REDIS_PORT: Optional[str] = Field(default="6379", validation_alias="REDIS_PORT")
    REDIS_NAME: Optional[str] = Field(..., validation_alias="REDIS_NAME")
    REDIS_PASSWORD: Optional[str] = Field(..., validation_alias="REDIS_PASSWORD")
    REDIS_HOST: Optional[str] = Field(..., validation_alias="REDIS_HOST")
    REDIS_LOCATION: Optional[str] = Field(..., validation_alias="REDIS_LOCATION")
    REDIS_URL: Optional[str] = Field(..., validation_alias="REDIS_URL")

    # ── LLM ───────────────────────────────────────────────────────────────────
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = Field(default="", validation_alias="GEMINI_API_KEY")
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ── GCP ───────────────────────────────────────────────────────────────────
    GCP_PROJECT: Optional[str] = Field(default="", validation_alias="GCP_PROJECT")
    GCP_LOCATION: Optional[str] = Field(default="us-central-1", validation_alias="GCP_LOCATION")
    VERTEX_DATASTORE_ID: Optional[str] = Field(default="", validation_alias="VERTEX_DATASTORE_ID")

    # ── Phoenix ───────────────────────────────────────────────────────────────
    # "cloud" | "local" | "noop"
    PHOENIX_MODE: Optional[str] = Field(default="local", validation_alias="PHOENIX_MODE")
    PHOENIX_API_KEY: Optional[str] = Field(default="", validation_alias="PHOENIX_API_KEY")
    PHOENIX_PROJECT_NAME: Optional[str] = Field(default="clinical-copilot", validation_alias="PHOENIX_API_KEY") #: str = "clinical-copilot"
    PHOENIX_CLOUD_ENDPOINT: str = "https://app.phoenix.arize.com"
    PHOENIX_LOCAL_ENDPOINT: str = "http://localhost:6006"
    PHOENIX_TRIAGE_PROMPT_NAME: str = "triage-system-prompt"

    @property
    def phoenix_endpoint(self) -> str:
        """
        Resolved Phoenix endpoint based on mode.
        Container and MCP client use this — not the raw field.
        """
        if self.PHOENIX_MODE == "local":
            return self.PHOENIX_LOCAL_ENDPOINT
        return self.PHOENIX_CLOUD_ENDPOINT

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql://{self.PG_USERNAME}:{self.PG_PASSWORD}"
            f"@{self.PG_HOSTNAME}:{self.PG_PORT}/{self.PG_DB_NAME}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()