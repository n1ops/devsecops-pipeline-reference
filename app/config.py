from pydantic_settings import BaseSettings

# INTENTIONAL: B105 - hardcoded default secret key for scanner demonstration
_DEFAULT_SECRET = "development-secret-key-change-in-production"


class Settings(BaseSettings):
    APP_NAME: str = "DevSecOps Task API"
    DATABASE_URL: str = "sqlite:///./tasks.db"
    SECRET_KEY: str = _DEFAULT_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
