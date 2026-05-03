# Troubleshooting

## No reduction occurs

Run `hermes tool-slimmer doctor`. If the core selector hook is unavailable, Hermes Tool Slimmer can benchmark and log dry-run decisions but cannot replace schemas sent to providers.

## A required tool is missing

Add it to `tool_slimmer.always_include` or increase `top_k`. The selector never resurrects tools that Hermes already disabled.

## Selector errors

Keep `fail_open: true` for normal use. Errors then preserve the original full schema list.
