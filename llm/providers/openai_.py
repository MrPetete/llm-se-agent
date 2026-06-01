# llm/providers/openai_.py
import os
from openai import OpenAI

DEFAULT_MODEL = "gpt-4o-mini"


def call(prompt: str, model: str | None = None, system: str | None = None):
    model = model or DEFAULT_MODEL

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content, response.usage
