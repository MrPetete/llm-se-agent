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

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


settings = Settings()
