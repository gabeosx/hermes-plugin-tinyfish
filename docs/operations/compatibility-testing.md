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

CI builds the plugin wheel and tests it on Python 3.12 against the minimum
packaged `hermes-agent==0.18.2`, packaged `0.19.0`, and the official Hermes
0.20.0 source release tag. Hermes 0.20.0 is installed through its supported
editable source path because it is not published on PyPI and rejects wheel
builds. Each job uses an isolated `HERMES_HOME` to verify:

- entry-point plugin discovery and enablement;
- setup with `--yes --skip-login` and no secrets;
- non-secret `status --json` output; and
- non-live `doctor --json` success;
- registration of `pre_llm_call` without new model-callable tools; and
- diagnostics schema 3 routing/update fields without an update request in CI.

This is an offline configuration/load check. It does not replace the live
release gates below.

## Fresh Install and Update Paths

Fresh Git install:

```bash
hermes plugins install gabeosx/hermes-plugin-tinyfish/hermes --enable
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
   environment, and run
   `hermes tinyfish doctor --live --transport mcp`.
2. REST-only: omit TinyFish MCP configuration, supply an API key through the
   disposable environment, and run
   `hermes tinyfish doctor --live --transport rest`.

Search and Fetch run independently. The command must exit nonzero if either
fails. Record which transport was used without recording credentials.
When MCP tools are initially absent, one live diagnostic run must make at most
one plugin-triggered discovery attempt; Fetch must not immediately repeat a
failed Search discovery. Concurrent provider calls in one process must share
one in-flight plugin discovery attempt.

Confirm Hermes resolves both `web_search` and `web_extract` to `tinyfish` and
does not fall back to Firecrawl, Tavily, or another provider.

## Turn Routing and Update Awareness

With TinyFish MCP configured, invoke the registered `pre_llm_call` hook or run
a conversational smoke test and verify that the marked context describes:

- generic `web_search` / `web_extract` for ordinary tasks; and
- native TinyFish MCP `search` / `fetch_content` for provider-specific filters,
  selectors, formats, pagination, links/images, caching, and timeouts.

Invoke the hook with empty history and confirm it returns one marked routing
block. Invoke it again with that result in a prior message's `api_content` and
confirm it does not return another routing copy. Remove the marked message to
simulate compression and confirm the hook reinjects one copy. An
outdated-version notice must appear at most once per process and compose even
when routing is already present. Multiple tool calls inside one turn must not
produce additional context copies. Disable `tinyfish.routing_context` and
confirm new routing injection stops without unregistering either web provider.

Update tests must use a disposable `HERMES_HOME` and mocked release responses
or seeded cache data. Verify Git installs recommend
`hermes plugins update web-tinyfish`, PyPI installs recommend the Python/pip
upgrade command, and copied or package-manager-owned installs receive only the
release link. A stale or missing cache must start one daemon refresh without
delaying plugin load. Fresh, corrupt, concurrent, offline, and unwritable-cache
cases must remain nonfatal. `NO_UPDATE_NOTIFIER=1`, CI, and unit-test
environments must suppress the background request.

## OAuth Recovery and Discovery Gate

When testing a real authorization failure, never copy or print token files.
Record only the sanitized failure category and commands/exit codes:

```bash
hermes tinyfish doctor --live --transport mcp
hermes tinyfish reauth
# In the affected session:
/reload-mcp
hermes tinyfish doctor --live --transport mcp
```

For headless authorization, copy the complete URL without manually editing its
`state`, PKCE challenge, or other characters. If terminal selection inserts
line breaks, remove only whitespace before opening the URL. A second
authorization URL before success means the first flow failed; stop rather than
mixing callback URLs from different attempts.

Failure-injection coverage must verify that explicit OAuth errors remain
classifiable when wrapped in a task-group/exception-group container. A grouped
generic HTTP 400 must remain `unknown`. State mismatch must be treated as an
authorization failure, but tests must never weaken or bypass the state check.

The core login command's human-readable result and the MCP-only doctor are the
authoritative signals. Do not treat shell status 0 alone as proof that a token
was saved.

Test CLI, TUI, gateway, and plugin diagnostics on the minimum and latest
supported Hermes versions. The private lazy-discovery shim may be removed only
when each surface registers TinyFish before its first provider call, public
`ctx.dispatch_tool` reaches Search and Fetch, and reload recovers a parked
server without plugin-triggered discovery. If any condition fails, retain the
shim and update the public-API gap report rather than patching Hermes.

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
- routing-context registration/opt-out and update-check/cache result;
- retired-key detection/reset result;
- Browser policy and paid-check result, if explicitly approved;
- gateway restart and sanitized-log result; and
- skipped checks with reasons.

## References

- [Hermes plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
- [Hermes MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
- [TinyFish MCP integration](https://docs.tinyfish.ai/mcp-integration)
