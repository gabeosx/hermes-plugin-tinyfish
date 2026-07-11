# Compatibility Testing

Use this runbook to verify the TinyFish plugin against Hermes installs and
upgrades, including provider selection, MCP/REST routing, migration behavior,
Browser policy, and gateway loading.

## Boundaries

- Plugin source is this repository, or `HERMES_PLUGIN_TINYFISH_ROOT` when set.
- Prefer the `hermes` command on `PATH` for user-path checks.
- Use `HERMES_SOURCE_ROOT` only when a Hermes source checkout is needed for
  reference; do not modify Hermes core.
- Use disposable `HERMES_HOME` directories for destructive setup/migration
  tests.
- Never print `TINYFISH_API_KEY`, OAuth tokens, CDP URLs, signed URLs, or other
  connection credentials.

## Automated Compatibility Baseline

CI builds the plugin wheel, installs it with `hermes-agent==0.18.2` on Python
3.12, and uses an isolated `HERMES_HOME` to verify:

- entry-point plugin discovery and enablement;
- setup with `--yes --skip-login` and no secrets;
- non-secret `status --json` output; and
- non-live `doctor --json` success.

This is an offline configuration/load check. It does not replace the live
release gates below.

## Fresh Install and Update Paths

Fresh Git install:

```bash
hermes plugins install gabeosx/hermes-plugin-tinyfish --enable
hermes tinyfish setup
```

Update an existing installation:

```bash
hermes plugins list --plain --no-bundled
hermes plugins update web-tinyfish
hermes tinyfish status --json
```

For the `0.2.1` upgrade fixture, seed the old policy keys before updating:

```yaml
tinyfish:
  credit_policy:
    agent: request
    browser: allow
    profile_setup: deny
    model_tools: request
```

After update, status must report the three retired keys without modifying the
file. Then run:

```bash
hermes tinyfish credits reset
hermes tinyfish status --json
```

The resulting policy must contain only `browser: deny`. Do not delete or
modify remote TinyFish runs, profiles, credentials, or saved state.

## Provider and Transport Checks

Expected provider selection:

```yaml
web:
  search_backend: tinyfish
  extract_backend: tinyfish
```

Expected plugin-managed MCP configuration:

```yaml
mcp_servers:
  tinyfish:
    url: https://agent.tinyfish.ai/mcp
    auth: oauth
    tools:
      include: [search, fetch_content]
      resources: false
      prompts: false
```

Verify both modes separately:

1. MCP-only: complete OAuth setup, remove REST fallback from the disposable
   environment, and run `hermes tinyfish doctor --live`.
2. REST-only: omit TinyFish MCP configuration, supply an API key through the
   disposable environment, and run `hermes tinyfish doctor --live`.

Search and Fetch run independently. The command must exit nonzero if either
fails. Record which transport was used without recording credentials.

Confirm Hermes resolves both `web_search` and `web_extract` to `tinyfish` and
does not fall back to Firecrawl, Tavily, or another provider.

## Browser Check

Browser testing is separate because it may consume credits:

```bash
hermes tinyfish credits set browser request
hermes tinyfish doctor --live-paid
```

Obtain explicit approval at test time. The check must create and close exactly
one Browser session. It must refuse under `deny`, request approval under
`request`, accept `allow`, and fail if creation or cleanup fails. Output and
logs must not expose session IDs or connection URLs.

TinyFish Agent and Browser Context Profile behavior are not tested: those
surfaces are intentionally absent from the plugin.

## Gateway Behavior

After changing plugin loading or provider registration, restart the gateway:

```bash
hermes gateway restart
```

Verify a healthy replacement process and inspect sanitized logs for import,
registration, stale-tool, or provider-selection errors. Confirm the plugin
registers Search/Fetch and Browser providers but no TinyFish Agent tools.

## Compatibility Report

Record a sanitized report containing:

- date and operator;
- OS, Python version, Hermes version/SHA, plugin version/SHA, and install path;
- each command and exit code;
- fresh-install or update path;
- MCP or REST transport for Search and Fetch;
- resolved Search and Extract providers;
- retired-key detection/reset result;
- Browser policy and paid-check result, if explicitly approved;
- gateway restart and sanitized-log result; and
- skipped checks with reasons.

## References

- [Hermes plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
- [Hermes MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
- [TinyFish MCP integration](https://docs.tinyfish.ai/mcp-integration)
