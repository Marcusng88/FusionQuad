"""Tests for Deep Agents model selection."""

import app.core.model_selection as model_selection
from app.core.model_selection import resolve_deepagents_model


def test_uses_gemini_when_google_api_key_present(monkeypatch):
    model_selection._load_dotenv.cache_clear()
    monkeypatch.delenv("DEEPAGENTS_MODEL", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.setenv("MINIMAX_MODEL", "")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(model_selection, "_load_dotenv", lambda: {})

    assert resolve_deepagents_model("fallback:model") == "google_genai:gemini-2.5-flash"


def test_prefers_minimax_when_runtime_is_available(monkeypatch):
    model_selection._load_dotenv.cache_clear()
    monkeypatch.delenv("DEEPAGENTS_MODEL", raising=False)
    monkeypatch.setenv("MINIMAX_API_KEY", "minimax-key")
    monkeypatch.setenv("MINIMAX_MODEL", "minimax:minimax-m1")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(model_selection, "_load_dotenv", lambda: {})
    monkeypatch.setattr(model_selection, "_model_runtime_available", lambda model: model.startswith("minimax:"))

    assert resolve_deepagents_model("fallback:model") == "minimax:minimax-m1"


def test_falls_back_to_gemini_when_minimax_runtime_is_unavailable(monkeypatch):
    model_selection._load_dotenv.cache_clear()
    monkeypatch.delenv("DEEPAGENTS_MODEL", raising=False)
    monkeypatch.setenv("MINIMAX_API_KEY", "minimax-key")
    monkeypatch.setenv("MINIMAX_MODEL", "minimax:minimax-m1")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(model_selection, "_load_dotenv", lambda: {})
    monkeypatch.setattr(model_selection, "_model_runtime_available", lambda model: not model.startswith("minimax:"))

    assert resolve_deepagents_model("fallback:model") == "google_genai:gemini-2.5-flash"


def test_reads_gemini_key_from_dotenv_when_process_env_is_empty(monkeypatch):
    model_selection._load_dotenv.cache_clear()
    monkeypatch.delenv("DEEPAGENTS_MODEL", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(model_selection, "_load_dotenv", lambda: {"GEMINI_API_KEY": "gemini-key"})

    assert resolve_deepagents_model("fallback:model") == "google_genai:gemini-2.5-flash"
