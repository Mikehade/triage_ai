from src.config.base import Settings


class ProductionSettings(Settings):
    APP_ENV: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    VERSION: str = "0.1.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["*"]
    PHOENIX_MODE: str = "cloud"