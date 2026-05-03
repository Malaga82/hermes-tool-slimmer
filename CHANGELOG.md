# Changelog

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
