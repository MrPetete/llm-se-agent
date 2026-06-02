# llm/providers/qwen.py
import os
from openai import OpenAI

DEFAULT_MODEL = "qwen-max"

_VALID_QWEN_MODELS = {"qwen-max", "qwen-plus", "qwen-turbo", "qwen-long"}


def call(prompt: str, model: str | None = None, system: str | None = None):
    model = model or DEFAULT_MODEL

    if model not in _VALID_QWEN_MODELS:
        raise ValueError(
            f"'{model}' is not a valid Qwen model. "
            f"Valid options: {sorted(_VALID_QWEN_MODELS)}. "
            f"If you meant to use a different provider, set "
            f"LLM_PROVIDER=openai or LLM_PROVIDER=anthropic in your .env."
        )

    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content, response.usage
