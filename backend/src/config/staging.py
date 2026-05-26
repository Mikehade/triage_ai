from src.config.base import Settings


class StagingSettings(Settings):
    APP_ENV: str = "staging"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    VERSION: str = "0.1.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["*"]
    PHOENIX_MODE: str = "cloud"