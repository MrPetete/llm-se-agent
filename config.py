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

    # Pricing — USD per 1M tokens (source: Alibaba Cloud Model Studio, 2026-06-10)
    # qwen-max: flat rate. qwen-plus: ≤128K tier (lowest). qwen-turbo: flat rate.
    # Update these if the team switches models or Alibaba changes rates.
    # Reference: https://www.alibabacloud.com/help/en/model-studio/model-pricing
    llm_cost_input_per_1m: float = 0.345   # qwen-max default
    llm_cost_output_per_1m: float = 1.377  # qwen-max default

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


settings = Settings()
