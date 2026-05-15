# hermes-tool-slimmer — Fork Malaga82

Fork of [alias8818/hermes-tool-slimmer](https://github.com/alias8818/hermes-tool-slimmer) with custom patches for:

1. **Core patch updated for Hermes v0.13.0** — original patch failed 4/8 hunks
2. **Italian alias expansion** — BM25 tokenizer expands Italian queries to English for better tool matching
3. **Auto-expanding dictionary** — cron script uses LLM to add new Italian→English mappings
4. **Extra call sites covered** — 4 external `self.tools` references the original patch missed

## Quick Start

### 1. Install plugin

```bash
# From this repo
cd /opt/data
git clone https://github.com/Malaga82/hermes-tool-slimmer.git
cd hermes-tool-slimmer
/opt/hermes/.venv/bin/pip install -e .

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

The script:
- Reads unmapped Italian tokens logged by the tokenizer
- Sends them to an LLM (default: deepseek/deepseek-v4-flash via local proxy)
- Appends new entries to the alias YAML file
- Reloads the dictionary without restart

Environment variables for the expansion script:

| Variable | Default | Description |
|----------|---------|-------------|
| `EXPAND_ALIASES_API_URL` | `https://api.z.ai/api/coding/paas/v4/chat/completions` | LLM API endpoint |
| `EXPAND_ALIASES_MODEL` | `glm-5-turbo` | Model for translations |
| `GLM_API_KEY` | (from env) | API key for zai/GLM |
| `TOOL_SLIMMER_ALIASES` | `$HERMES_HOME/tool-slimmer-it-aliases.yaml` | Path to alias dictionary |
| `TOOL_SLIMMER_ALIASES_DISABLED` | (unset) | Set `1`/`true` to disable alias expansion |

## What's changed from upstream

| Change | Files | Why |
|--------|-------|-----|
| Core patch rewritten | `docs/hermes-core-selector-hook.patch` | 4/8 hunks failed on Hermes v0.13.0 |
| Italian alias expansion | `src/hermes_tool_slimmer/aliases.py` | Italian queries didn't match English tool descriptions |
| Tokenizer patched | `src/hermes_tool_slimmer/tokenizer.py` | Calls aliases.expand_tokens() on query tokens |
| Auto-expand script | `expand_aliases.py` | LLM-powered dictionary growth |
| Alias dictionary | `aliases/it-en.yaml` | 70+ Italian→English mappings |
| Extra call sites | patch covers lines 10399, 11973, 12019, 14843 | Original patch missed 4 `self.tools` refs |

## Architecture

```
User message (Italian)
       │
       ▼
  tokenizer.py
  ├─ Split into tokens
  ├─ aliases.expand_tokens() → add English equivalents
  │   "cerca" → ["cerca", "search", "find", "query"]
  └─ Return expanded token list
       │
       ▼
  selector.py (BM25)
  ├─ Score each tool schema against expanded tokens
  ├─ Select top_k (12) by score
  ├─ Add always_include tools (5)
  └─ Return filtered schema list
       │
       ▼
  API call with ~17 tools instead of 57
  Token savings: ~72-99%
```

## Safety (fail-open)

If anything goes wrong, Hermes works normally with all 57 tools:

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

If the dry-run fails (Hermes code changed significantly), the plugin still works — it just won't filter tools until the patch is updated.
