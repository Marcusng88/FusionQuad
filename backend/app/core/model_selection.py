"""Helpers for choosing the Deep Agents chat model from environment."""

from __future__ import annotations

from functools import lru_cache
from importlib.util import find_spec
import os
from pathlib import Path

from dotenv import dotenv_values

_DEFAULT_GEMINI_MODEL = "google_genai:gemini-2.5-flash"
_DEFAULT_MINIMAX_MODEL = "minimax:minimax-m1"


def resolve_deepagents_model(default_model: str) -> str:
    explicit_model = _read_env("DEEPAGENTS_MODEL")
    if explicit_model:
        return explicit_model

    minimax_model = _read_env("MINIMAX_MODEL") or _DEFAULT_MINIMAX_MODEL
    if _has_any_key("MINIMAX_API_KEY") and _model_runtime_available(minimax_model):
        return minimax_model

    gemini_model = _read_env("GEMINI_MODEL") or _DEFAULT_GEMINI_MODEL
    if _has_any_key("GOOGLE_API_KEY", "GEMINI_API_KEY") and _model_runtime_available(gemini_model):
        return gemini_model

    return default_model


def _has_any_key(*names: str) -> bool:
    return any(_read_env(name) for name in names)


def _read_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    return str(_load_dotenv().get(name, "")).strip()


def _model_runtime_available(model_spec: str) -> bool:
    provider, _, _ = model_spec.partition(":")
    if provider == "google_genai":
        return find_spec("langchain_google_genai") is not None
    if provider == "minimax":
        return find_spec("langchain_minimax") is not None or find_spec("litellm") is not None
    return True


@lru_cache
def _load_dotenv() -> dict[str, str | None]:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return {}
    return dotenv_values(env_path)
