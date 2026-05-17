# Changelog

## 0.3.4 - 2026-05-17

Upstream v0.3.4 merge (12 commits) preserving Malaga82 customisations (Italian aliases, custom scripts, core patch v0.13.0).

### Metrics (production — 15–17 May 2026)

| Metric | Value |
|---|---|
| Tool-slimmer calls | 851 |
| Tools available | 59 |
| Tools selected (avg) | 17 |
| Selection latency | 9.4 ms/call |
| Schema tokens before | 14,029,459 |
| Schema tokens after | 6,927,338 |
| Schema tokens saved | 7,102,121 |
| Reduction | 50.6% |
| API calls logged | 713 |
| Avg prompt tokens | 67,431 |
| Cache read tokens | 43,150,656 |
| Net new tokens total | 4,927,713 |

### Added

- Two-layer synonym system (Italian → English + semantic expansion).
- 70 Italian aliases for keyword-based tool matching.
- Custom scripts: `check-tool-slimmer-patch.py`, `check-slimmer-flag.sh`, `apply_slimmer_patch.py`.
- Startup checker + cron Discord notification for patch status.
- Core patch updated for Hermes v0.13.0 (`_build_api_kwargs` patch).

### Changed

- Merged upstream v0.3.4 (12 commits) keeping Malaga82 fork customisations.
- Hardened CLI schema and config loading edge cases.
- Fixed standalone selection and Anthropic metrics.
- Fail-open design: if patch not applied after Hermes update, everything works normally without token savings.

## 0.2.0 - 2026-05-15

Dashboard and operations release.

### Added

- Hermes dashboard plugin with status, health checks, recent selection decisions, selected-tool visibility, and estimated schema-token savings.
- Dashboard backend API routes for Tool Slimmer status, session-filtered summaries, full audit summaries, and raw recent events.
- Durable JSONL decision logging under `$HERMES_HOME/tool-slimmer/decisions.jsonl`.
- One-command local installer/repair script and deterministic troubleshooting report script.
- GitHub Actions test workflow plus README badges and professional README hero image.

### Changed

- Dashboard headline totals now exclude probe/test events without a Hermes `session_id`; full audit totals remain available as `all_summary`.
- README and docs now clearly label savings as estimated schema-token savings, not guaranteed billable-token savings.

### Tested

- Added tests for decision logging, session-filtered summary accounting, dashboard API routes, and existing selector/provider behavior.

## 0.1.0 - 2026-05-03

Initial public release.

### Added

- Hermes plugin entry point `tool-slimmer`.
- Deterministic tokenizer, corpus builder, local BM25 ranker, and selector.
- Config loader for `tool_slimmer` settings in Hermes config files.
- CLI commands for status, doctor, index, select, benchmark, and config recommendations.
- Slash command and JSON tool handlers.
- Metrics for schema byte/token reduction estimates.
- Anthropic Tool Search helpers with explicit provider capability gating.
- JSON index store with checksum-based rebuilds.
- Upstreamable Hermes core selector-hook patch artifact.
- Documentation, examples, and unit tests.
