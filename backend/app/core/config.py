from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AI_PROVIDER_NAMES = ("groq", "gemini", "nvidia")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(min_length=1)
    environment: Literal["development", "test", "production"] = "development"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    # Comma-separated list of exact origins; wildcards are rejected.
    cors_origins: str = "http://localhost:3000"
    max_resume_size_mb: int = Field(default=5, ge=1, le=20)
    # Marks the session cookie Secure (sent over HTTPS only). Turn on whenever the API is
    # served over HTTPS; plain-HTTP local development needs it off.
    auth_cookie_secure: bool = False

    # AI model gateway. Empty AI_PROVIDERS = AI disabled (resume processing still works).
    # Comma-separated, in order: the first is the primary, the rest are fallbacks.
    ai_providers: str = ""
    ai_timeout_seconds: float = Field(default=20, gt=0, le=120)  # per attempt
    ai_max_retries: int = Field(default=1, ge=0, le=5)  # per provider, transient errors only
    ai_max_output_tokens: int = Field(default=8192, ge=256, le=32768)
    groq_api_key: SecretStr | None = None
    groq_model: str | None = None
    gemini_api_key: SecretStr | None = None
    gemini_model: str | None = None
    nvidia_api_key: SecretStr | None = None
    nvidia_model: str | None = None

    @property
    def ai_provider_list(self) -> list[str]:
        return [p.strip().lower() for p in self.ai_providers.split(",") if p.strip()]

    @model_validator(mode="after")
    def check_ai_providers(self) -> Self:
        names = self.ai_provider_list
        if len(set(names)) != len(names):
            raise ValueError("AI_PROVIDERS lists a provider twice")
        for name in names:
            if name not in AI_PROVIDER_NAMES:
                raise ValueError(f"AI_PROVIDERS: unknown provider {name!r}")
            # Names only: never echo a key value in an error.
            if not getattr(self, f"{name}_api_key") or not getattr(self, f"{name}_model"):
                raise ValueError(f"AI provider {name!r} needs {name.upper()}_API_KEY and "
                                 f"{name.upper()}_MODEL")
        return self

    @property
    def max_resume_bytes(self) -> int:
        return self.max_resume_size_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS must list explicit origins, not '*'")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
