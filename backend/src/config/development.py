from src.config.base import Settings


class DevSettings(Settings):
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    VERSION: str = "0.1.0-dev"
    PORT: int = 8022
    CORS_ORIGINS: list[str] = ["*"]

    # Use noop MCP and local DB in development by default
    # Override in .env to test against real Phoenix
    PHOENIX_MODE: str = "noop"