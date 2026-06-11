# llm/wrapper.py
import os
import time
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from .providers import REGISTRY
from .logging_ import log_call

load_dotenv()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def ask(
    prompt: str,
    model: str | None = None,
    system: str | None = None,
    agent: str | None = None,
) -> str:
    provider_name = os.getenv("LLM_PROVIDER", "qwen").lower()

    if provider_name not in REGISTRY:
        raise ValueError(
            f"Unknown LLM_PROVIDER='{provider_name}'. "
            f"Expected one of: {list(REGISTRY)}"
        )

    provider = REGISTRY[provider_name]
    start = time.time()
    try:
        reply, usage = provider.call(prompt, model=model, system=system)
        elapsed = round(time.time() - start, 3)
        log_call(
            provider=provider_name,
            model=model or provider.DEFAULT_MODEL,
            prompt=prompt,
            elapsed=elapsed,
            agent=agent,
            reply=reply,
            usage=usage,
            success=True,
        )
        return reply
    except Exception as exc:
        elapsed = round(time.time() - start, 3)
        log_call(
            provider=provider_name,
            model=model or provider.DEFAULT_MODEL,
            prompt=prompt,
            elapsed=elapsed,
            agent=agent,
            success=False,
            error=str(exc),
        )
        raise
