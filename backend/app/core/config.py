"""
Core application configuration using Pydantic Settings.

This module centralizes all configuration for the application including:
- Database settings
- Azure OpenAI settings
- MindsDB settings
- Langfuse settings
- Agent configuration
- HITL settings
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    postgres_db: str = Field(default="agentic_bi")
    postgres_user: str = Field(default="admin")
    postgres_password: str = Field(default="devpassword123")
    postgres_host: str = Field(default="postgres")
    postgres_port: int = Field(default=5432)

    @property
    def url(self) -> str:
        """Get database URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class RedisSettings(BaseSettings):
    """Redis configuration."""

    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379)
    redis_password: Optional[str] = Field(default=None)
    redis_db: int = Field(default=0)

    @property
    def url(self) -> str:
        """Get Redis URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AzureOpenAISettings(BaseSettings):
    """Azure OpenAI configuration."""

    azure_openai_api_key: str = Field(..., description="Azure OpenAI API key")
    azure_openai_endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    azure_openai_deployment: str = Field(default="gpt-4", description="Deployment name")
    azure_openai_api_version: str = Field(default="2023-05-15", description="API version")

    # Agent-specific LLM settings
    agent_temperature: float = Field(default=0.1, description="Temperature for agent LLM calls")
    agent_max_tokens: int = Field(default=2000, description="Max tokens for agent responses")
    agent_timeout: int = Field(default=30, description="Timeout in seconds for LLM calls")
    agent_retry_attempts: int = Field(default=3, description="Number of retry attempts")

    @field_validator("azure_openai_endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        """Ensure endpoint doesn't have trailing slash."""
        return v.rstrip("/")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class MindsDBSettings(BaseSettings):
    """MindsDB configuration."""

    mindsdb_api_url: str = Field(..., description="MindsDB API URL")
    mindsdb_timeout: int = Field(default=60, description="Timeout for MindsDB queries in seconds")
    mindsdb_max_retries: int = Field(default=3, description="Max retry attempts for failed queries")

    @field_validator("mindsdb_api_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL doesn't have trailing slash."""
        return v.rstrip("/")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class LangfuseSettings(BaseSettings):
    """Langfuse observability configuration."""

    langfuse_host: str = Field(..., description="Langfuse host URL")
    langfuse_public_key: str = Field(..., description="Langfuse public key")
    langfuse_secret_key: str = Field(..., description="Langfuse secret key")
    langfuse_enabled: bool = Field(default=True, description="Enable/disable Langfuse tracing")

    @field_validator("langfuse_host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Ensure host doesn't have trailing slash."""
        return v.rstrip("/")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class OPASettings(BaseSettings):
    """OPA (Open Policy Agent) configuration."""

    opa_url: str = Field(..., description="OPA server URL")
    opa_timeout: int = Field(default=5, description="Timeout for OPA requests in seconds")

    @field_validator("opa_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL doesn't have trailing slash."""
        return v.rstrip("/")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class JWTSettings(BaseSettings):
    """JWT authentication configuration."""

    jwt_secret: str = Field(..., description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=1440, description="Access token expiration")
    jwt_refresh_expiration_days: int = Field(default=7, description="Refresh token expiration")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AgentSettings(BaseSettings):
    """Agent-specific configuration."""

    # Confidence thresholds
    sql_confidence_threshold: float = Field(
        default=0.8,
        description="Confidence threshold for auto-approving SQL queries",
        ge=0.0,
        le=1.0
    )

    # Query limits
    default_query_limit: int = Field(default=1000, description="Default row limit for queries")
    max_query_limit: int = Field(default=10000, description="Maximum row limit for queries")

    # Cache settings
    schema_cache_ttl: int = Field(default=7200, description="Schema cache TTL in seconds (2 hours)")
    query_cache_ttl: int = Field(default=3600, description="Query cache TTL in seconds (1 hour)")

    # Performance limits
    max_response_time_ms: int = Field(default=5000, description="Max response time in milliseconds")
    max_memory_mb: int = Field(default=512, description="Max memory usage in MB")
    max_concurrent_sessions: int = Field(default=10, description="Max concurrent agent sessions")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class HITLSettings(BaseSettings):
    """Human-in-the-Loop configuration."""

    # Timeout settings
    default_intervention_timeout: int = Field(
        default=300,
        description="Default timeout for human interventions in seconds (5 minutes)"
    )
    max_intervention_timeout: int = Field(
        default=900,
        description="Maximum timeout for human interventions in seconds (15 minutes)"
    )

    # Behavior settings
    timeout_fallback: str = Field(
        default="abort",
        description="Fallback behavior on timeout: 'abort', 'continue', 'auto_approve'"
    )

    # Enable/disable HITL
    hitl_enabled: bool = Field(default=True, description="Enable human-in-the-loop interventions")

    @field_validator("timeout_fallback")
    @classmethod
    def validate_fallback(cls, v: str) -> str:
        """Validate fallback behavior."""
        allowed = ["abort", "continue", "auto_approve"]
        if v not in allowed:
            raise ValueError(f"timeout_fallback must be one of: {allowed}")
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AppSettings(BaseSettings):
    """General application settings."""

    env: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=True, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # CORS
    cors_origins: str = Field(default="http://localhost:3000", description="Comma-separated CORS origins")

    # Rate limiting
    rate_limit_per_minute: int = Field(default=100, description="Rate limit per minute")
    rate_limit_burst: int = Field(default=200, description="Rate limit burst size")

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class Settings(BaseSettings):
    """
    Master settings class that aggregates all configuration.

    Usage:
        from app.core.config import settings

        # Access configuration
        db_url = settings.database.url
        llm_key = settings.azure_openai.azure_openai_api_key
    """

    # Aggregate all settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    azure_openai: AzureOpenAISettings = Field(default_factory=AzureOpenAISettings)
    mindsdb: MindsDBSettings = Field(default_factory=MindsDBSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    opa: OPASettings = Field(default_factory=OPASettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    hitl: HITLSettings = Field(default_factory=HITLSettings)
    app: AppSettings = Field(default_factory=AppSettings)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Global settings instance
settings = Settings()


# Convenience function for testing/overriding settings
def get_settings() -> Settings:
    """Get settings instance (useful for dependency injection in FastAPI)."""
    return settings
