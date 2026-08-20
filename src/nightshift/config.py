"""Configuration management for Night Shift."""

from enum import Enum
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SandboxMode(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"


class Settings(BaseSettings):
    """Application runtime settings and environment parameters."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Project paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])
    data_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2] / ".nightshift")

    # GitHub Integration
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    default_repo: str = Field(default="demo/sample-repo", alias="NIGHTSHIFT_DEFAULT_REPO")

    # AWS Bedrock / LLM Configuration
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        alias="BEDROCK_MODEL_ID",
    )

    # Sandbox Configuration
    sandbox_mode: SandboxMode = Field(default=SandboxMode.LOCAL, alias="SANDBOX_MODE")
    sandbox_docker_image: str = Field(default="python:3.11-slim", alias="SANDBOX_DOCKER_IMAGE")
    sandbox_timeout_seconds: int = Field(default=60, alias="SANDBOX_TIMEOUT_SECONDS")
    max_fix_attempts: int = Field(default=3, alias="MAX_FIX_ATTEMPTS")

    # Storage
    db_path: Path = Field(default=Path("./nightshift.db"), alias="NIGHTSHIFT_DB_PATH")

    # Server
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")


# Global settings singleton
settings = Settings()
