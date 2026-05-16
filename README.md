# hermes-tool-slimmer — Fork Malaga82

Fork of [alias8818/hermes-tool-slimmer](https://github.com/alias8818/hermes-tool-slimmer) (upstream v0.3.4 merged) with custom patches for:

1. **Core patch updated for Hermes v0.13.0** — original patch failed 4/8 hunks
2. **Italian alias expansion** — BM25 tokenizer expands Italian queries to English for better tool matching
3. **Auto-expanding dictionary** — cron script uses LLM to add new Italian→English mappings
4. **Extra call sites covered** — 4 external `self.tools` references the original patch missed
5. **Startup patch checker** — notifies on Discord if core patch is missing after Hermes update
6. **JSONL log rotation** — decisions capped at 5000, usage at 2000 entries
7. **Post-API usage logging** — captures actual prompt/net/cache tokens per request

![Hermes](https://img.shields.io/badge/Hermes-dashboard%20plugin-111827)

## Quick Start

### 1. Install plugin

```bash
# From this repo
cd /opt/data
git clone https://github.com/Malaga82/hermes-tool-slimmer.git
cd hermes-tool-slimmer
uv pip install --python /opt/hermes/.venv/bin/python3 -e .

# Symlink to Hermes plugins
ln -sf /opt/data/hermes-tool-slimmer /opt/data/plugins/tool-slimmer
```

### 2. Apply core patch to Hermes

```bash
cd /opt/hermes
patch -p1 --dry-run -f -i /opt/data/hermes-tool-slimmer/docs/hermes-core-selector-hook.patch
# If dry-run passes:
patch -p1 -f -i /opt/data/hermes-tool-slimmer/docs/hermes-core-selector-hook.patch
```

### 3. Configure

Add to `config.yaml`:

```yaml
tool_slimmer:
  enabled: true
  mode: keyword
  top_k: 12
  always_include:
    - terminal
    - read_file
    - write_file
    - patch
    - search_files

plugins:
  enabled:
    - tool-slimmer
```

### 4. Italian aliases (optional but recommended)

Copy the alias dictionary to `$HERMES_HOME`:

```bash
cp /opt/data/hermes-tool-slimmer/aliases/it-en.yaml $HERMES_HOME/tool-slimmer-it-aliases.yaml
```

The tokenizer automatically loads this file and expands Italian tokens with English equivalents for BM25 matching.

### 5. Auto-expand dictionary via cron (optional)

```bash
# Dry run — see what would be added
python /opt/data/hermes-tool-slimmer/expand_aliases.py --dry-run

# Actually expand
python /opt/data/hermes-tool-slimmer/expand_aliases.py

# Cron (e.g., weekly)
# 0 3 * * 0 /opt/hermes/.venv/bin/python /opt/data/hermes-tool-slimmer/expand_aliases.py
```

Environment variables for the expansion script:

| Variable | Default | Description |
|----------|---------|-------------|
| `EXPAND_ALIASES_API_URL` | `https://api.z.ai/api/coding/paas/v4/chat/completions` | LLM API endpoint |
| `EXPAND_ALIASES_MODEL` | `glm-5-turbo` | Model for translations |
| `GLM_API_KEY` | (from env) | API key for zai/GLM |
| `TOOL_SLIMMER_ALIASES` | `$HERMES_HOME/tool-slimmer-it-aliases.yaml` | Path to alias dictionary |
| `TOOL_SLIMMER_ALIASES_DISABLED` | (unset) | Set `1`/`true` to disable alias expansion |

### 6. Dashboard

Tool Slimmer includes a Hermes dashboard plugin for monitoring selection decisions, schema-token savings, and health status.

```bash
# Install dashboard plugin
cp -r dashboard-plugin/tool-slimmer $HERMES_HOME/plugins/tool-slimmer-dashboard/
```

See [`docs/dashboard-plugin.md`](docs/dashboard-plugin.md) for details.

## What's changed from upstream

| Change | Files | Why |
|--------|-------|-----|
| Core patch rewritten | `docs/hermes-core-selector-hook.patch` | 4/8 hunks failed on Hermes v0.13.0 |
| Italian alias expansion | `src/hermes_tool_slimmer/aliases.py` | Italian queries didn't match English tool descriptions |
| Tokenizer patched | `src/hermes_tool_slimmer/tokenizer.py` | Calls aliases.expand_tokens() on query tokens |
| Auto-expand script | `expand_aliases.py` | LLM-powered dictionary growth |
| Alias dictionary | `aliases/it-en.yaml` | 70+ Italian→English mappings |
| Extra call sites | patch covers lines 10399, 11973, 12019, 14843 | Original patch missed 4 `self.tools` refs |
| Startup patch checker | `scripts/check-tool-slimmer-patch.py` | Notifies on Discord if patch missing after update |
| Cron flag checker | `scripts/check-slimmer-flag.sh` | Hermes cron checks for missing patch flag |

## What's merged from upstream (v0.2.0 → v0.3.4)

| Feature | Description |
|---------|-------------|
| Synonym expansion | `expand_query_tokens()` with `BUILTIN_ALIASES` in selector (browse→browser, website→web, etc.) |
| Config guardrails | `min_total_tools` (default 20), `min_estimated_reduction_percent` (default 5%) |
| Config validation | Strict type checking for top_k, min_total_tools, min_estimated_reduction_percent |
| Score details | Per-tool breakdown: bm25, name_boost, toolset_boost, parameter_boost, alias_boost |
| Expanded query tokens | Logged in decisions for debugging |
| Malformed schema hardening | Non-dict schemas, missing fields handled gracefully |
| Duplicate tool name detection | Warning + first-schema-wins |
| no_relevant_match guardrail | Returns only always_include when no BM25 match, with reason tracking |
| Dashboard index controls | Rebuild from Hermes tools, checksum, preview |
| Log rotation | decisions.jsonl capped at 5000, actual_usage.jsonl at 2000 |

## Architecture — Two-Layer Synonym System

```
User message (Italian)
       │
       ▼
  Layer 1: tokenizer.py (our aliases.py — it→en)
  ├─ Split into tokens
  ├─ aliases.expand_tokens() → add English equivalents
  │   "cerca internet" → [..., "search", "find", "query", "web", "http", "url", "online"]
  └─ Return expanded token list
       │
       ▼
  Layer 2: selector.py (upstream BUILTIN_ALIASES — en→en)
  ├─ expand_query_tokens() → expand English synonyms
  │   "browse website" → [..., "browser", "navigate", "url", "web", "page"]
  ├─ BM25 scoring with alias_boost
  ├─ Select top_k (12) by score + boosts
  ├─ Add always_include tools (5)
  └─ Return filtered schema list
       │
       ▼
  API call with ~17 tools instead of 59
  Token savings: ~49% average (up to 87%)
       │
       ▼
  integration.py → metrics.py → decisions.jsonl → Dashboard plugin
```

## Proven Results

Based on 537 decisions over ~14 hours (zai/glm-5.1):

| Metric | Value |
|--------|-------|
| Total tools | 59 |
| Average selected/turn | 15.3 |
| Average reduction | 49.0% |
| Token schema saved | 4.049.277 |
| Cache hit rate | ~90% of prompt tokens |

## Safety (fail-open)

If anything goes wrong, Hermes works normally with all 59 tools:

- Plugin not installed → no filtering
- Plugin crashes → all tools pass through
- Core patch not applied → original code unchanged
- Alias dictionary missing → tokenization works without expansion

## After Hermes updates

After `hermes update`, re-apply the core patch:

```bash
cd /opt/hermes
patch -p1 --dry-run -f -i /opt/data/hermes-tool-slimmer/docs/hermes-core-selector-hook.patch
# If dry-run passes:
patch -p1 -f -i /opt/data/hermes-tool-slimmer/docs/hermes-core-selector-hook.patch
```

If the dry-run fails (Hermes code changed significantly), the plugin still works — it just won't filter tools until the patch is updated. The startup checker will notify you on Discord.

## Merge Strategy

Upstream: `alias8818/hermes-tool-slimmer` (remote: `upstream`)

```bash
git fetch upstream
git merge upstream/main --no-commit  # review before committing
```

**Files to PRESERVE** (our custom additions):
- `src/hermes_tool_slimmer/aliases.py`
- `src/hermes_tool_slimmer/tokenizer.py`
- `aliases/it-en.yaml`
- `expand_aliases.py`
- `scripts/check-tool-slimmer-patch.py`
- `scripts/check-slimmer-flag.sh`
- `README.md`
