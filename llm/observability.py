# llm/observability.py
"""Patch all agent LLM call paths to log with agent tags.

Agent A  -> CrewAI -> LiteLLM -> OpenAI-compatible endpoint (patched via LiteLLM callback)
Agents B, C -> dashscope.Generation.call directly        (patched via monkey-patch)

Usage in orchestrator/main.py:
    from llm.observability import setup, set_agent
    setup()          # call once at pipeline start
    set_agent("agent_a")
    ... run agent A ...
    set_agent("agent_b")
    ... run agent B ...
"""
import time
import types
from .logging_ import log_call

_current_agent: str | None = None
_installed = False


def set_agent(name: str | None) -> None:
    """Set the agent tag applied to all LLM calls until the next set_agent() call."""
    global _current_agent
    _current_agent = name


def setup() -> None:
    """Install logging hooks. Safe to call multiple times — installs only once."""
    global _installed
    if _installed:
        return
    _install_dashscope_patch()
    _install_litellm_callback()
    _installed = True


def _make_usage(prompt_tokens, completion_tokens, total_tokens):
    return types.SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )


def _install_dashscope_patch() -> None:
    """Wrap dashscope.Generation.call for Agents B and C."""
    try:
        import dashscope
    except ImportError:
        return

    original = dashscope.Generation.call

    def patched(*args, **kwargs):
        model = kwargs.get("model") or (args[0] if args else "qwen-max")
        prompt = kwargs.get("prompt") or (args[1] if len(args) > 1 else "")
        start = time.time()
        try:
            response = original(*args, **kwargs)
            elapsed = round(time.time() - start, 3)
            raw = getattr(response, "usage", None)
            usage = _make_usage(
                prompt_tokens=getattr(raw, "input_tokens", None),
                completion_tokens=getattr(raw, "output_tokens", None),
                total_tokens=getattr(raw, "total_tokens", None),
            )
            log_call(
                provider="qwen",
                model=str(model),
                prompt=str(prompt),
                elapsed=elapsed,
                agent=_current_agent,
                success=True,
                usage=usage,
            )
            return response
        except Exception as exc:
            elapsed = round(time.time() - start, 3)
            log_call(
                provider="qwen",
                model=str(model),
                prompt=str(prompt),
                elapsed=elapsed,
                agent=_current_agent,
                success=False,
                error=str(exc),
            )
            raise

    dashscope.Generation.call = patched


def _install_litellm_callback() -> None:
    """Register LiteLLM success/failure callbacks for Agent A (CrewAI)."""
    try:
        import litellm
    except ImportError:
        return

    def on_success(kwargs, response_obj, start_time, end_time):
        try:
            elapsed = (end_time - start_time).total_seconds()
            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages") or []
            prompt = str(messages[-1].get("content", "")) if messages else ""
            raw = getattr(response_obj, "usage", None)
            usage = _make_usage(
                prompt_tokens=getattr(raw, "prompt_tokens", None),
                completion_tokens=getattr(raw, "completion_tokens", None),
                total_tokens=getattr(raw, "total_tokens", None),
            )
            log_call(
                provider="qwen",
                model=str(model),
                prompt=prompt,
                elapsed=elapsed,
                agent=_current_agent,
                success=True,
                usage=usage,
            )
        except Exception:
            pass

    def on_failure(kwargs, response_obj, start_time, end_time):
        try:
            elapsed = (end_time - start_time).total_seconds()
            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages") or []
            prompt = str(messages[-1].get("content", "")) if messages else ""
            log_call(
                provider="qwen",
                model=str(model),
                prompt=prompt,
                elapsed=elapsed,
                agent=_current_agent,
                success=False,
                error=str(response_obj),
            )
        except Exception:
            pass

    litellm.success_callback.append(on_success)
    litellm.failure_callback.append(on_failure)
