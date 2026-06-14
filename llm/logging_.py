# llm/logging_.py
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

_CST = timezone(timedelta(hours=8))

LOG_PATH = Path("logs/llm_calls.jsonl")
LOG_PATH.parent.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(message)s")
_logger = logging.getLogger(__name__)


def log_call(
    provider: str,
    model: str,
    prompt: str,
    elapsed: float,
    agent: str | None = None,
    reply: str | None = None,
    usage=None,
    success: bool = True,
    error: str | None = None,
):
    entry = {
        "timestamp": datetime.now(_CST).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "provider": provider,
        "model": model,
        "agent": agent,
        "success": success,
        "error": error,
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
        "elapsed_seconds": elapsed,
        "prompt_preview": prompt[:120],
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    if success:
        _logger.info(
            f"[LLM] {provider}/{model} | {elapsed}s | "
            f"{usage.total_tokens if usage else '?'} tokens"
        )
    else:
        _logger.warning(f"[LLM] {provider}/{model} | FAILED after {elapsed}s | {error}")
