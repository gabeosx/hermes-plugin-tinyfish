# Compatibility Testing

Use this runbook when verifying the TinyFish plugin against a Hermes install or
source checkout, Hermes upgrades, gateway behavior, plugin install/update
behavior, MCP OAuth behavior, or provider selection.

## Boundaries

- Plugin source: this repository, or `HERMES_PLUGIN_TINYFISH_ROOT` when set.
- Hermes install: prefer the `hermes` command on `PATH` for user-path checks.
- Hermes source checkout: optional; use `HERMES_SOURCE_ROOT` when a local
  checkout is required for reference or upgrade testing.
- Do not modify Hermes core files for TinyFish compatibility.
- Do not print secrets such as `TINYFISH_API_KEY` or OAuth tokens.

## Install or Update Through Hermes

Using the installed Hermes command:

```bash
hermes plugins list
hermes plugins update web-tinyfish
```

For a fresh user-path install outside this checkout, the primary install path
is:

```bash
hermes plugins install gabeosx/hermes-plugin-tinyfish --enable
```

Hermes currently has runtime plugin discovery rather than a full marketplace or
search index, so use the repository identifier directly.

## Setup and Status

Verify setup and status:

```bash
hermes tinyfish status
hermes tinyfish doctor
```

The expected Hermes config selects TinyFish for both web search and extraction:

```yaml
web:
  search_backend: tinyfish
  extract_backend: tinyfish
```

The expected MCP server endpoint is:

```text
https://agent.tinyfish.ai/mcp
```

OAuth MCP is preferred. REST fallback uses `TINYFISH_API_KEY` only when MCP
OAuth is unavailable or not configured.

## Live Check

Run the live doctor only when credentials are available:

```bash
hermes tinyfish doctor --live
```

`doctor --live` should prove that Hermes can search and fetch with TinyFish. In
the report, say whether the check used MCP OAuth or REST fallback, but do not
print tokens or API keys.

`doctor --live` intentionally tests only Search and Fetch. TinyFish docs
currently describe those capabilities as free, but this is based on current
documentation and may change.

Credit-risking Agent, Browser, and Browser Context Profile setup checks require
explicit policy changes:

```bash
hermes tinyfish credits set browser request
hermes tinyfish doctor --live-paid
```

`doctor --live-paid` must refuse when the relevant policy is `deny`, trigger
Hermes approval when the policy is `request`, and avoid printing signed URLs or
secrets.

## Gateway Behavior

If provider registration, plugin loading, or long-running Hermes gateway
behavior may be affected, verify gateway restart/load behavior after updating
the plugin.

Report whether Hermes is using TinyFish rather than Firecrawl, Tavily, or any
other provider.

If `browser.cloud_provider: tinyfish` is configured, verify that browser tool
calls are blocked, approval-gated, or allowed according to
`tinyfish.credit_policy.browser`.

## References

- [Hermes plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
- [Hermes MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
- [TinyFish MCP integration](https://docs.tinyfish.ai/mcp-integration)
