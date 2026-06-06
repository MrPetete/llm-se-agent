# llm/providers/__init__.py
from . import qwen, openai_, anthropic_

REGISTRY = {
    "qwen": qwen,
    "openai": openai_,
    "anthropic": anthropic_,
}
