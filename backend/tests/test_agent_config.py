"""Tests for centralized agent model configuration (Opportunity 4)."""

import importlib
import importlib.util
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "app" / "agents" / "config.py"


def _load_config():
    """Load config.py directly (avoids triggering app.agents.__init__ heavy deps)."""
    spec = importlib.util.spec_from_file_location("agents_config", _CONFIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.AGENT_MODELS


def test_default_models_are_claude_sonnet_4_6(monkeypatch):
    monkeypatch.delenv("PLANNER_MODEL", raising=False)
    monkeypatch.delenv("CONTROLLER_MODEL", raising=False)
    monkeypatch.delenv("AUDITOR_MODEL", raising=False)
    models = _load_config()
    assert models["planner"] == "claude-sonnet-4-6"
    assert models["controller"] == "claude-sonnet-4-6"
    assert models["auditor"] == "claude-sonnet-4-6"


def test_planner_model_overridable_by_env(monkeypatch):
    monkeypatch.setenv("PLANNER_MODEL", "claude-opus-4-7")
    monkeypatch.delenv("CONTROLLER_MODEL", raising=False)
    monkeypatch.delenv("AUDITOR_MODEL", raising=False)
    models = _load_config()
    assert models["planner"] == "claude-opus-4-7"
    assert models["controller"] == "claude-sonnet-4-6"


def test_controller_model_overridable_by_env(monkeypatch):
    monkeypatch.delenv("PLANNER_MODEL", raising=False)
    monkeypatch.setenv("CONTROLLER_MODEL", "claude-haiku-4-5-20251001")
    monkeypatch.delenv("AUDITOR_MODEL", raising=False)
    models = _load_config()
    assert models["controller"] == "claude-haiku-4-5-20251001"
    assert models["planner"] == "claude-sonnet-4-6"


def test_auditor_model_overridable_by_env(monkeypatch):
    monkeypatch.delenv("PLANNER_MODEL", raising=False)
    monkeypatch.delenv("CONTROLLER_MODEL", raising=False)
    monkeypatch.setenv("AUDITOR_MODEL", "claude-opus-4-7")
    models = _load_config()
    assert models["auditor"] == "claude-opus-4-7"


def test_all_three_agents_have_entries():
    models = _load_config()
    assert set(models.keys()) >= {"planner", "controller", "auditor"}


def test_agent_files_do_not_define_default_model():
    """Regression guard: _DEFAULT_MODEL must not appear in agent node files."""
    agents_dir = Path(__file__).parent.parent / "app" / "agents"
    files = {
        "planner/node.py": agents_dir / "planner" / "node.py",
        "controller/node.py": agents_dir / "controller" / "node.py",
        "auditor/agent.py": agents_dir / "auditor" / "agent.py",
    }
    for label, path in files.items():
        content = path.read_text()
        assert "_DEFAULT_MODEL" not in content, f"{label} still defines _DEFAULT_MODEL"
