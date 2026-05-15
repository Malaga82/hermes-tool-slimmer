# Troubleshooting

## Dashboard savings look too high

Dashboard savings are estimated schema-token savings, not guaranteed billable-token savings. Tool Slimmer computes them from serialized tool-schema JSON bytes divided by 4 before and after selection. Actual provider input-token and billing deltas can differ because tokenizers, prompt caching, system prompts, conversation history, and provider-specific tool serialization are outside this estimate.

The dashboard headline excludes probe/test events that do not have a Hermes `session_id`. Use the dashboard API's `all_summary` field when you need a full audit of every logged decision.

## No reduction occurs

Run `hermes tool-slimmer doctor`. If the core selector hook is unavailable, Hermes Tool Slimmer can benchmark and log dry-run decisions but cannot replace schemas sent to providers.

Also check `tool_slimmer.min_total_tools` and `tool_slimmer.min_estimated_reduction_percent`. By default, Tool Slimmer skips catalogs with fewer than 20 tools and skips ranked selections under 5% estimated schema reduction. This is intentional for cron/small-toolset paths where the overhead is not worth the tiny savings.

## Tool index looks stale

Open the Tool Slimmer dashboard page and click **Rebuild From Hermes Tools**. The card shows the index path, count, checksum, and last-updated time. The live selector still ranks the current request's tool schemas in memory, so a stale persisted index affects visibility and troubleshooting, not request-time safety.

## A required tool is missing

Add it to `tool_slimmer.always_include` or increase `top_k`. The selector never resurrects tools that Hermes already disabled.

In keyword mode, the selector only matches text present in tool names, toolsets, descriptions, and parameter schemas. If users naturally say "browse" but the tool is described only as "navigate", add both terms to the tool description or move to a semantic selector mode when one is available.

`always_include` is intentionally outside the `top_k` budget. For example, five always-included tools plus `top_k: 8` can return up to thirteen selected tools.

## Selector errors

Keep `fail_open: true` for normal use. Errors then preserve the original full schema list.
