import sys
import logging

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# INTENTIONAL: B105 - hardcoded default secret key for scanner demonstration
_DEFAULT_SECRET = "development-secret-key-change-in-production"


class Settings(BaseSettings):
    APP_NAME: str = "DevSecOps Task API"
    DATABASE_URL: str = "sqlite:///./tasks.db"
    SECRET_KEY: str = _DEFAULT_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}

    def get_allowed_origins(self) -> list[str]:
        if self.ALLOWED_ORIGINS:
            return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]
        if self.DEBUG:
            return ["*"]
        return []


settings = Settings()

# Startup security check: reject default secret key in non-debug mode
if not settings.DEBUG and settings.SECRET_KEY == _DEFAULT_SECRET:
    logger.critical(
        "FATAL: SECRET_KEY is set to the default development value. "
        "Set SECRET_KEY environment variable before running in production."
    )
    sys.exit(1)
