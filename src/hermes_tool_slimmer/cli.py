from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from .anthropic_tool_search import supports_anthropic_tool_search
from .config import ToolSlimmerConfig, config_path, load_config
from .corpus import tool_name
from .index_store import IndexStore
from .metrics import reduction_metrics
from .selector import ToolSelector


def _load_schemas(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    data = yaml.safe_load(Path(path).read_text())
    if isinstance(data, dict):
        return data.get("tools") or data.get("schemas") or []
    return data or []


def _tool_names(schemas: list[dict[str, Any]]) -> set[str]:
    return {tool_name(schema) for schema in schemas}


def _check(status: str, message: str, detail: object | None = None) -> dict[str, object]:
    item: dict[str, object] = {"status": status, "message": message}
    if detail is not None:
        item["detail"] = detail
    return item


def run_doctor(
    config_arg: str | None = None,
    schemas_path: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, object]:
    checks: dict[str, dict[str, object]] = {}
    cfg: ToolSlimmerConfig | None = None
    try:
        cfg = load_config(config_arg)
        checks["config"] = _check("pass", "tool_slimmer config is valid", {"mode": cfg.mode, "top_k": cfg.top_k})
    except Exception as exc:
        checks["config"] = _check("fail", "tool_slimmer config is invalid", str(exc))
        cfg = ToolSlimmerConfig(enabled=False)

    checks["hermes_importable"] = _check(
        "pass" if importlib.util.find_spec("hermes_cli") else "warn",
        "Hermes Python modules are importable" if importlib.util.find_spec("hermes_cli") else "Hermes Python modules were not found in this environment",
    )

    enabled_detail: object = "config file not found"
    enabled_status = "warn"
    target = Path(config_arg).expanduser() if config_arg else config_path()
    if target.exists():
        try:
            data = yaml.safe_load(target.read_text()) or {}
            enabled = data.get("plugins", {}).get("enabled", []) if isinstance(data, dict) else []
            enabled_status = "pass" if "tool-slimmer" in enabled else "warn"
            enabled_detail = enabled
        except Exception as exc:
            enabled_status = "warn"
            enabled_detail = f"config unreadable: {exc}"
    checks["plugin_enabled"] = _check(
        enabled_status,
        "tool-slimmer is listed in plugins.enabled"
        if enabled_status == "pass"
        else "tool-slimmer is not listed in plugins.enabled",
        enabled_detail,
    )

    store = IndexStore()
    try:
        probe = store.root / ".doctor-write-test" if store.root else store.path.parent / ".doctor-write-test"
        probe.write_text("ok")
        probe.unlink()
        index = store.load()
        checks["index_store"] = _check("pass", "index directory is readable/writable", {"path": str(store.path), "indexed_tools": (index or {}).get("total_tools", 0)})
    except Exception as exc:
        checks["index_store"] = _check("fail", "index directory is not readable/writable", str(exc))

    schemas = _load_schemas(schemas_path)
    if schemas:
        names = _tool_names(schemas)
        missing = [name for name in cfg.always_include if name not in names]
        checks["always_include"] = _check("pass" if not missing else "warn", "always-included tools exist in supplied schemas" if not missing else "some always-included tools are absent from supplied schemas", missing)
    else:
        checks["always_include"] = _check("warn", "no schemas supplied; cannot validate always_include")

    selector_supported = False
    try:
        import hermes_cli.plugins as plugins  # type: ignore[import-not-found]

        selector_supported = "select_tool_schemas" in getattr(plugins, "VALID_HOOKS", set())
        checks["core_selector_hook"] = _check(
            "pass" if selector_supported else "warn",
            "Hermes core advertises select_tool_schemas"
            if selector_supported
            else "Hermes core does not advertise select_tool_schemas; apply docs/hermes-core-selector-hook.patch",
        )
    except Exception:
        checks["core_selector_hook"] = _check(
            "warn",
            "Hermes core not importable here; apply/check docs/hermes-core-selector-hook.patch",
        )

    if cfg.mode == "anthropic_tool_search":
        supported = supports_anthropic_tool_search(
            provider, model, cfg.anthropic.tool_search_supported
        )
        if supported:
            checks["anthropic_tool_search"] = _check(
                "pass",
                "provider path supports Anthropic Tool Search",
                {"provider": provider, "model": model},
            )
        else:
            checks["anthropic_tool_search"] = _check(
                "fail",
                "anthropic_tool_search mode requires native Anthropic provider or explicit tool_search_supported for this provider path",
                {"provider": provider, "model": model},
            )
    else:
        checks["anthropic_tool_search"] = _check("pass", "Anthropic Tool Search mode is not active")
    return {"ok": all(v["status"] != "fail" for v in checks.values()), "checks": checks}


def setup_argparse(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", help="Path to Hermes config.yaml")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--schemas")
    doctor.add_argument("--provider")
    doctor.add_argument("--model")
    index = sub.add_parser("index")
    index_sub = index.add_subparsers(dest="index_command", required=True)
    rebuild = index_sub.add_parser("rebuild")
    rebuild.add_argument("--schemas", required=True)
    show = index_sub.add_parser("show")
    show.add_argument("--top", type=int, default=20)
    select = sub.add_parser("select")
    select.add_argument("query")
    select.add_argument("--schemas")
    bench = sub.add_parser("benchmark")
    bench.add_argument("--prompts", required=True)
    bench.add_argument("--schemas")
    sub.add_parser("recommend-config")


def handle_cli(args: argparse.Namespace) -> int:
    if args.command == "doctor":
        print(
            json.dumps(
                run_doctor(
                    getattr(args, "config", None),
                    getattr(args, "schemas", None),
                    getattr(args, "provider", None),
                    getattr(args, "model", None),
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    cfg = load_config(getattr(args, "config", None))
    if args.command == "status":
        store = IndexStore()
        index = store.load() or {}
        print(json.dumps({"enabled": cfg.enabled, "mode": cfg.mode, "top_k": cfg.top_k, "index_path": str(store.path), "total_tools_indexed": index.get("total_tools", 0), "core_integration": "active when Hermes exposes select_tool_schemas hook or applies docs/hermes-core-selector-hook.patch"}, indent=2))
        return 0
    if args.command == "index":
        store = IndexStore()
        if args.index_command == "rebuild":
            payload = store.rebuild(_load_schemas(args.schemas))
            print(json.dumps({"path": str(store.path), "checksum": payload["checksum"], "total_tools": payload["total_tools"]}, indent=2))
            return 0
        index = store.load() or {"documents": []}
        print(json.dumps(index.get("documents", [])[: args.top], indent=2))
        return 0
    if args.command == "select":
        schemas = _load_schemas(args.schemas)
        result = ToolSelector(cfg).select(args.query, schemas)
        print(json.dumps({"selected": result.selected_names, "scores": result.scores, "fail_open": result.fail_open}, indent=2, sort_keys=True))
        return 0
    if args.command == "benchmark":
        schemas = _load_schemas(args.schemas)
        prompts = yaml.safe_load(Path(args.prompts).read_text()).get("prompts", [])
        rows = []
        selector = ToolSelector(cfg)
        for prompt in prompts:
            result = selector.select(prompt["text"], schemas)
            metrics = reduction_metrics(cfg.mode, schemas, result.selected, result.always_included)
            expected = set(prompt.get("expected_any", []))
            rows.append({"name": prompt.get("name"), "selected": result.selected_names, "expected_included": bool(expected & set(result.selected_names)) if expected else None, "metrics": metrics})
        print(json.dumps({"benchmarks": rows}, indent=2))
        return 0
    if args.command == "recommend-config":
        print(yaml.safe_dump({"tool_slimmer": {"enabled": True, "mode": "keyword", "top_k": 8, "always_include": cfg.always_include, "min_total_tools": cfg.min_total_tools, "min_estimated_reduction_percent": cfg.min_estimated_reduction_percent, "fail_open": True, "dry_run": False}}, sort_keys=False))
        return 0
    raise ValueError(f"Unknown command {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hermes tool-slimmer")
    setup_argparse(parser)
    return handle_cli(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
