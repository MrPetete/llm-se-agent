# llm/wrapper.py
import os
import json
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

# ── Logging setup ───────────────────────────────────────────────────────────
LOG_PATH = Path("logs/llm_calls.jsonl")
LOG_PATH.parent.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ── DashScope client (OpenAI-compatible) ────────────────────────────────────
_client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


# ── Core function ────────────────────────────────────────────────────────────
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def ask(prompt: str, model: str = "qwen-max", system: str | None = None) -> str:
    """
    Send a prompt to the LLM and return the text response.

    Args:
        prompt:  The user message / instruction.
        model:   DashScope model name (default: qwen-max).
        system:  Optional system prompt to set context/persona.

    Returns:
        The model's reply as a plain string.

    Raises:
        RuntimeError: if all 3 retry attempts fail.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    start = time.time()

    response = _client.chat.completions.create(
        model=model,
        messages=messages,
    )

    elapsed = round(time.time() - start, 3)
    reply = response.choices[0].message.content

    # ── Structured log entry ────────────────────────────────────────────────
    usage = response.usage
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": model,
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
        "elapsed_seconds": elapsed,
        "prompt_preview": prompt[:120],
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    logger.info(
        f"[LLM] {model} | {elapsed}s | "
        f"{usage.total_tokens if usage else '?'} tokens"
    )

    return reply