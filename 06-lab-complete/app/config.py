"""Production config — 12-Factor: tất cả từ environment variables."""
import os
import logging
from dataclasses import dataclass, field


@dataclass
class Settings:
    # Server
    HOST: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    PORT: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    ENVIRONMENT: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    DEBUG: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # App
    APP_NAME: str = field(default_factory=lambda: os.getenv("APP_NAME", "Production AI Agent"))
    APP_VERSION: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))
    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # LLM
    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    LLM_MODEL: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))

    # Security
    AGENT_API_KEY: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", "dev-key-change-me"))
    JWT_SECRET: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "dev-jwt-secret"))
    ALLOWED_ORIGINS: list[str] = field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "*").split(",")
    )

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    )

    # Budget
    MONTHLY_BUDGET_USD: float = field(
        default_factory=lambda: float(os.getenv("MONTHLY_BUDGET_USD", "10.0"))
    )
    COST_PER_REQUEST_USD: float = field(
        default_factory=lambda: float(os.getenv("COST_PER_REQUEST_USD", "0.01"))
    )

    # Storage
    REDIS_URL: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://redis:6379/0")
    )

    def validate(self):
        logger = logging.getLogger(__name__)

        if self.ENVIRONMENT == "production":
            if self.AGENT_API_KEY == "dev-key-change-me":
                raise ValueError("AGENT_API_KEY must be set in production!")
            if self.JWT_SECRET == "dev-jwt-secret":
                raise ValueError("JWT_SECRET must be set in production!")

        if not self.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set — using mock LLM")

        return self


settings = Settings().validate()