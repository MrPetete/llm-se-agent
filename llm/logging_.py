# llm/logging_.py
import json
import time
import logging
from pathlib import Path

LOG_PATH = Path("logs/llm_calls.jsonl")
LOG_PATH.parent.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(message)s")
_logger = logging.getLogger(__name__)


def log_call(
    provider: str,
    model: str,
    prompt: str,
    reply: str,
    usage,
    elapsed: float,
    agent: str | None = None,
):
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "provider": provider,
        "model": model,
        "agent": agent,
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
        "elapsed_seconds": elapsed,
        "prompt_preview": prompt[:120],
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _logger.info(
        f"[LLM] {provider}/{model} | {elapsed}s | "
        f"{usage.total_tokens if usage else '?'} tokens"
    )
