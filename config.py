from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # LLM
    llm_provider: Literal["qwen", "openai", "anthropic"] = "qwen"
    qwen_model: str = "qwen-max"
    dashscope_api_key: str = Field(default="", repr=False)
    openai_api_key: str = Field(default="", repr=False)
    anthropic_api_key: str = Field(default="", repr=False)

    # Paths
    log_dir: Path = Path("./logs")
    output_dir: Path = Path("./output")

    # Sandbox (used in W4)
    sandbox_timeout_seconds: int = 30
    sandbox_image: str = "llm-se-agent-sandbox:latest"
    # When True, the sandbox refuses to fall back to subprocess if Docker is
    # unavailable (returns sandbox_mode="docker_required_failed"). Default False:
    # Docker is preferred but not mandatory, so the pipeline/CI never breaks.
    sandbox_require_docker: bool = False

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


settings = Settings()
