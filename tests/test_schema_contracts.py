from __future__ import annotations

from hermes_tool_slimmer.config import VALID_MODES
from hermes_tool_slimmer.schemas import SELECT_SCHEMA


def test_select_schema_mode_enum_matches_config_modes() -> None:
    mode_schema = SELECT_SCHEMA["parameters"]["properties"]["mode"]
    assert set(mode_schema["enum"]) == VALID_MODES - {"eager"}
