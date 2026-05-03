import json

from hermes_tool_slimmer.commands import handle_slash_command
from hermes_tool_slimmer.config import ToolSlimmerConfig
from hermes_tool_slimmer.integration import maybe_register_selector_hook, select_tool_schemas_callback
from hermes_tool_slimmer.tools import tool_slimmer_select, tool_slimmer_status


def test_plugin_handlers_return_json_strings(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    status = tool_slimmer_status({})
    select = tool_slimmer_select({"query": "read", "schemas": [{"name": "read_file", "description": "Read"}]})
    slash = handle_slash_command("select read", schemas=[{"name": "read_file", "description": "Read"}])
    assert json.loads(status)["ok"] is True
    assert json.loads(select)["ok"] is True
    assert json.loads(slash)["ok"] is True


def test_integration_contract_returns_none_when_disabled():
    out = select_tool_schemas_callback("read", [], [{"name": "read_file"}], "model", "platform", config=ToolSlimmerConfig(enabled=False))
    assert out is None


def test_integration_contract_dry_run_preserves_original_behavior():
    out = select_tool_schemas_callback("read", [], [{"name": "read_file"}], "model", "platform", config=ToolSlimmerConfig(dry_run=True))
    assert out is None


def test_anthropic_mode_falls_back_to_keyword_for_openrouter():
    schemas = [
        {"name": "read_file", "description": "Read files"},
        {"name": "github_search_code", "description": "Search code"},
        {"name": "slack_send_message", "description": "Send slack message"},
    ]
    out = select_tool_schemas_callback(
        "github search",
        [],
        schemas,
        "anthropic/claude-sonnet",
        "cli",
        provider="openrouter",
        config=ToolSlimmerConfig(mode="anthropic_tool_search", top_k=1, always_include=[]),
    )
    assert out == [schemas[1]]


def test_pre_llm_and_selector_hooks_registered():
    calls = []

    class Ctx:
        def register_hook(self, name, callback):
            calls.append((name, callback))

    assert maybe_register_selector_hook(Ctx()) is True
    assert [name for name, _ in calls] == ["pre_llm_call", "select_tool_schemas"]


def test_selector_hook_registration_fails_safe_when_unknown_hook_rejected():
    calls = []

    class Ctx:
        valid_hooks = {"pre_llm_call"}

        def register_hook(self, name, callback):
            calls.append(name)
            if name not in self.valid_hooks:
                raise ValueError(name)

    assert maybe_register_selector_hook(Ctx()) is False
    assert calls == ["pre_llm_call"]


def test_doctor_reports_invalid_config_without_crashing(tmp_path):
    from argparse import Namespace
    from hermes_tool_slimmer.cli import handle_cli

    path = tmp_path / "config.yaml"
    path.write_text("tool_slimmer:\n  mode: definitely_bad\n")
    assert handle_cli(Namespace(command="doctor", config=str(path), schemas=None, provider=None, model=None)) == 0


def test_doctor_uses_provider_model_for_anthropic_capability(tmp_path):
    from hermes_tool_slimmer.cli import run_doctor

    path = tmp_path / "config.yaml"
    path.write_text("tool_slimmer:\n  mode: anthropic_tool_search\n")
    openrouter = run_doctor(str(path), provider="openrouter", model="anthropic/claude")
    native = run_doctor(str(path), provider="anthropic", model="claude-sonnet")
    assert openrouter["checks"]["anthropic_tool_search"]["status"] == "fail"
    assert native["checks"]["anthropic_tool_search"]["status"] == "pass"


def test_doctor_reports_malformed_yaml_without_crashing(tmp_path):
    from hermes_tool_slimmer.cli import run_doctor

    path = tmp_path / "config.yaml"
    path.write_text("tool_slimmer:\n  mode: [bad\n")
    result = run_doctor(str(path))
    assert result["ok"] is False
    assert result["checks"]["config"]["status"] == "fail"
    assert result["checks"]["plugin_enabled"]["status"] == "warn"
