from hermes_tool_slimmer.config import ToolSlimmerConfig
from hermes_tool_slimmer.selector import ToolSelector


SCHEMAS = [
    {"name": "terminal", "toolset": "native", "description": "Run shell commands"},
    {"name": "read_file", "toolset": "native", "description": "Read a file"},
    {"name": "search_files", "toolset": "native", "description": "Search files in repo"},
    {"name": "github_search_code", "toolset": "github", "description": "Search GitHub code", "parameters": {"properties": {"query": {"description": "search query"}}}},
    {"name": "slack_send_message", "toolset": "slack", "description": "Send Slack message"},
]


def test_selector_always_includes_core_tools():
    cfg = ToolSlimmerConfig(top_k=3, always_include=["terminal", "read_file"])
    result = ToolSelector(cfg).select("github code search", SCHEMAS)
    assert result.selected_names[:2] == ["terminal", "read_file"]


def test_selector_respects_top_k_after_always_includes():
    cfg = ToolSlimmerConfig(top_k=2, always_include=["terminal"])
    result = ToolSelector(cfg).select("github code search", SCHEMAS)
    assert len(result.selected_names) == 3
    assert result.selected_names[0] == "terminal"


def test_selector_does_not_select_disabled_tools():
    cfg = ToolSlimmerConfig(top_k=5, always_include=[], disabled_toolsets=["github"])
    result = ToolSelector(cfg).select("github code search", SCHEMAS)
    assert "github_search_code" not in result.selected_names


def test_selector_fails_open_on_index_error(monkeypatch):
    cfg = ToolSlimmerConfig(top_k=2, always_include=[])
    selector = ToolSelector(cfg)
    monkeypatch.setattr(selector, "_eligible", lambda schemas: (_ for _ in ()).throw(RuntimeError("boom")))
    result = selector.select("anything", SCHEMAS)
    assert result.fail_open is True
    assert result.selected == SCHEMAS


def test_exact_tool_name_boost_selects_named_tool():
    cfg = ToolSlimmerConfig(top_k=1, always_include=[])
    result = ToolSelector(cfg).select("please use github_search_code", SCHEMAS)
    assert result.selected_names == ["github_search_code"]


def test_selector_respects_include_mcp_tools_flag():
    cfg = ToolSlimmerConfig(top_k=5, always_include=[], include_mcp_tools=False)
    schemas = [*SCHEMAS, {"name": "mcp_read_issue", "toolset": "mcp", "description": "Read MCP issue"}]
    result = ToolSelector(cfg).select("mcp issue", schemas)
    assert "mcp_read_issue" not in result.selected_names


def test_selector_respects_include_mcp_tools_for_mcp_server_metadata():
    cfg = ToolSlimmerConfig(top_k=5, always_include=[], include_mcp_tools=False)
    schemas = [*SCHEMAS, {"name": "issue_read", "mcp_server": "github", "description": "Read issue"}]
    result = ToolSelector(cfg).select("read github issue", schemas)
    assert "issue_read" not in result.selected_names


def test_selector_respects_include_mcp_tools_for_hermes_mcp_name_prefix():
    cfg = ToolSlimmerConfig(top_k=5, always_include=[], include_mcp_tools=False)
    schemas = [*SCHEMAS, {"name": "mcp_github_read_issue", "description": "Read issue"}]
    result = ToolSelector(cfg).select("read github issue", schemas)
    assert "mcp_github_read_issue" not in result.selected_names


def test_selector_respects_include_mcp_tools_for_plain_server_metadata():
    cfg = ToolSlimmerConfig(top_k=5, always_include=[], include_mcp_tools=False)
    schemas = [*SCHEMAS, {"name": "issue_read", "server": "github", "description": "Read issue"}]
    result = ToolSelector(cfg).select("read github issue", schemas)
    assert "issue_read" not in result.selected_names
