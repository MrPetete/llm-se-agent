# llm/providers/anthropic_.py
import os

DEFAULT_MODEL = "claude-sonnet-4-20250514"


def call(prompt: str, model: str | None = None, system: str | None = None):
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "Anthropic provider requires the anthropic package. "
            "Run: pip install anthropic"
        )

    model = model or DEFAULT_MODEL
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    kwargs = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)

    class _Usage:
        def __init__(self, r):
            self.prompt_tokens = r.usage.input_tokens
            self.completion_tokens = r.usage.output_tokens
            self.total_tokens = r.usage.input_tokens + r.usage.output_tokens

    return response.content[0].text, _Usage(response)
