# Hermes TinyFish Plugin

[![CI](https://github.com/gabeosx/hermes-plugin-tinyfish/actions/workflows/ci.yml/badge.svg)](https://github.com/gabeosx/hermes-plugin-tinyfish/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/hermes-plugin-tinyfish.svg)](https://pypi.org/project/hermes-plugin-tinyfish/)
[![Python](https://img.shields.io/pypi/pyversions/hermes-plugin-tinyfish.svg)](https://pypi.org/project/hermes-plugin-tinyfish/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Security Policy](https://img.shields.io/badge/Security-policy-green.svg)](SECURITY.md)

TinyFish Search and Fetch providers with plain-language tool routing, update
awareness, and optional TinyFish Browser infrastructure for
[Hermes Agent](https://hermes-agent.nousresearch.com/docs/).

Hermes remains the agent: it plans, chooses tools, and controls browser
interaction. This plugin supplies web data and, when explicitly enabled, a
remote browser session underneath Hermes's own browser loop.

This is an independent community plugin. It is not affiliated with, endorsed
by, or maintained by TinyFish or Hermes / Nous Research.

TinyFish documentation currently describes Search and Fetch as free and
Browser as credit-consuming. This plugin treats Search and Fetch as the safe
default entry point. Pricing and free-use assumptions are based only on current
TinyFish documentation and may change; Browser defaults to `deny`.

## Install

Hermes Git plugin install:

```bash
hermes plugins install gabeosx/hermes-plugin-tinyfish --enable
hermes tinyfish setup
```

Python package install:

```bash
pip install hermes-plugin-tinyfish
hermes plugins enable web-tinyfish
hermes tinyfish setup
```

## Update

Update an existing Hermes Git plugin installation:

```bash
hermes plugins update web-tinyfish
hermes tinyfish status
hermes tinyfish doctor
```

If the plugin was installed as a Python package instead, update it with:

```bash
python -m pip install --upgrade hermes-plugin-tinyfish
hermes tinyfish status
hermes tinyfish doctor
```

The plugin also performs a nonblocking update check when it loads. Git installs
are compared with the latest stable GitHub Release; Python package installs are
compared with the latest stable PyPI version. Results are cached for 24 hours
at `$HERMES_HOME/cache/web-tinyfish-update.json` in the active profile. If an
update is available, Hermes mentions it once on the first conversational turn
where the cached or background result is available. The plugin never installs
the update itself.

The check sends only the installed plugin version in its HTTP User-Agent. It
does not send Hermes configuration, TinyFish credentials, searches, fetched
URLs, or conversation content. Network and cache failures are silent. Disable
the check with `tinyfish.update_check: false` or the conventional
`NO_UPDATE_NOTIFIER=1` environment variable.

## Safe Default Setup

`hermes tinyfish setup` configures TinyFish for Hermes `web_search` and
`web_extract` only:

```yaml
mcp_servers:
  tinyfish:
    url: https://agent.tinyfish.ai/mcp
    auth: oauth
    tools:
      include: [search, fetch_content]
      resources: false
      prompts: false

web:
  search_backend: tinyfish
  extract_backend: tinyfish

tinyfish:
  routing_context: true
  update_check: true
  credit_policy:
    browser: deny
```

The plugin prefers TinyFish's hosted OAuth MCP server and falls back to REST
with `TINYFISH_API_KEY` when MCP OAuth is unavailable. It may save
`TINYFISH_API_KEY` to `~/.hermes/.env` if you choose API-key fallback.

Verify Search and Fetch:

```bash
hermes tinyfish doctor
hermes tinyfish doctor --live
hermes tinyfish doctor --live --transport mcp
hermes tinyfish doctor --live --transport rest
```

`doctor --live` runs independent Search and Fetch checks and exits nonzero if
either fails. The default `auto` transport remains MCP-first and may use the
REST fallback. Use `--transport mcp` to test OAuth without allowing REST to
hide an MCP failure, or `--transport rest` to test only the API-key path.

If MCP reports that authorization must be renewed:

```bash
hermes tinyfish reauth
```

The command replaces the current plugin CLI process with Hermes's supported
`hermes mcp login tinyfish` command; it does not start a nested Hermes process.
If a gateway or another Hermes process shares the same Hermes home, pause that
process and any supervisor or watchdog for the maintenance window. The plugin
does not stop host services automatically.

Complete the browser flow, restore and reload or restart affected Hermes
processes, then verify the recovered OAuth path with
`hermes tinyfish doctor --live --transport mcp`. The plugin never deletes,
rewrites, or validates Hermes's OAuth token files itself.

For browser authorization from a headless or remote terminal:

- Complete one authorization flow at a time and never combine an authorization
  URL with a callback URL from another attempt.
- Terminal wrapping is visual. Copy the entire URL and do not manually edit
  OAuth characters such as `state` or the PKCE challenge.
- If copied terminal text contains line breaks, remove only whitespace. In a
  local Blink shell on iOS/iPadOS, for example:

  ```bash
  pbpaste | tr -d '\r\n\t ' | pbcopy
  ```

- If Hermes prints another authorization URL before reporting success, stop
  that attempt rather than authorizing multiple URLs.
- Treat the MCP-only doctor as authoritative. Some Hermes versions can print
  an authentication failure while still returning shell status 0.

## Automatic Tool Routing

Talk to Hermes normally; you do not need to choose “the plugin” or “MCP.” When
an active context does not already contain the current routing version, the
plugin adds a short routing note that helps Hermes choose the narrowest tool
surface:

- “Find recent TinyFish documentation” uses Hermes `web_search`.
- “Read this page and summarize it” uses Hermes `web_extract`.
- “Search only these domains, in English, after this date, and return page 2”
  uses TinyFish MCP's native `search` tool because the generic search schema
  cannot express all of those controls.
- “Find research papers from these publication years” also uses native
  `search`, while “Fetch these URLs using this selector and conditional ETag”
  uses native `fetch_content`.

Hermes keeps the visible stored user message clean but persists the exact
API-bound message in an `api_content` sidecar for prompt-cache replay. The note
contains a versioned marker, so the hook does not add another copy while that
version remains in the active context. If compression removes the marked
message, the hook adds one fresh copy. Multiple tool calls inside a turn do not
run the hook again. Hermes still sees the real tool schemas and makes the final
choice; the plugin does not keyword-match the prompt or force a tool.

Routing guidance defaults on only when the plugin-managed TinyFish MCP server
is configured. Set `tinyfish.routing_context: false` to disable the guidance
without disabling the provider. This prevents new injections; a copy already
present in the active API context may remain until that context is reset or
compressed.

## Search and Fetch Options

Optional REST fallback defaults can be configured in `config.yaml`:

```yaml
tinyfish:
  search:
    location: US
    language: en
    recency_minutes: 1440
    domain_type: web
    page: 0
  fetch:
    format: markdown
    links: false
    image_links: false
    ttl: 3600
```

MCP remains the preferred path when configured. These options apply only to
REST fallback calls. They are fixed fallback defaults, not required settings
for ordinary requests and not a substitute for plain-language, per-request MCP
controls. The plugin does not add persistent include-domain, exclude-selector,
or similar parity settings.

## Optional Browser Provider

TinyFish Browser can supply remote browser infrastructure for Hermes after
explicit opt-in:

```yaml
browser:
  cloud_provider: tinyfish
tinyfish:
  credit_policy:
    browser: request
```

Browser policy values are:

- `deny`: fail closed; this is the default.
- `request`: use Hermes's approval flow for each `browser_*` tool invocation.
- `allow`: run Browser tools without per-invocation approval.

Manage the policy with:

```bash
hermes tinyfish credits status
hermes tinyfish credits set browser request
hermes tinyfish credits reset
```

`credits reset` restores `browser: deny` and removes retired Agent/Profile
policy keys left by plugin `0.2.x`.

## Why TinyFish Agent Is Not Included

TinyFish Agent performs delegated goal-based web automation. Hermes already
owns planning and browser interaction, so exposing a second agent loop through
this provider is duplicative and makes control, approval, and billing less
clear. The plugin therefore does not register TinyFish Agent tools or manage
Browser Context Profiles.

Users who specifically need TinyFish's delegated Agent, Profile, Vault, batch,
or streaming capabilities can configure TinyFish's full MCP service
independently in Hermes. Those tools are outside this plugin's setup, policy,
diagnostics, and compatibility guarantees. The plugin-managed `tinyfish` MCP
entry intentionally remains restricted to `search` and `fetch_content`.

## Diagnostics and Migration

```bash
hermes tinyfish status
hermes tinyfish usage
hermes tinyfish doctor --live
hermes tinyfish doctor --live --transport mcp
hermes tinyfish doctor --live-paid
```

- `status` is non-secret and reports ignored `0.2.x` policy keys under
  `retired_credit_policy_keys`.
- Status also reports whether routing and update checks are enabled, whether
  routing is active, the installed version, the cached latest version, and
  cached update availability. Reading status never performs an update request.
- `mcp_token_cached` reports only whether Hermes's expected cache file is
  present. It does not mean the access or refresh token is valid.
- `/tinyfish-status` shows non-networked status inside CLI or gateway sessions;
  `/tinyfish-status live` explicitly runs Search and Fetch checks.
- `usage` reads TinyFish Search and Fetch operation history independently and
  prints a labeled, paginated history for people. Use `usage --json` for the raw
  machine-readable response. It reports per-surface success or failure and is
  not Agent or Browser billing data.
- `doctor --live-paid` only creates and closes a TinyFish Browser session. It
  refuses under `deny`, requests approval under `request`, and never prints
  connection URLs or credentials.
- The former `agent` and `profiles` commands and model-callable Agent tools are
  intentionally removed. Existing remote TinyFish runs, profiles, credentials,
  and saved state are not changed.

## Upgrade Safety

This plugin uses public Hermes extension points:

- `ctx.register_web_search_provider(...)`
- `ctx.register_browser_provider(...)`
- `ctx.register_hook("pre_tool_call", ...)` for Browser credit policy
- `ctx.register_hook("pre_llm_call", ...)` for context-aware tool routing and
  update notices
- `ctx.register_cli_command(...)`
- `ctx.register_command(...)` for `/tinyfish-status`
- `ctx.dispatch_tool(...)` for registered TinyFish MCP calls
- Hermes MCP configuration under `mcp_servers`
- Hermes environment helpers for optional API-key fallback

It does not patch Hermes Agent, update scripts, Dockerfiles, or files inside a
Hermes installation or source checkout. A narrow legacy compatibility shim
still asks Hermes to discover configured MCP servers when TinyFish tools have
not been registered in the current process. It is retained because removing it
reintroduces a previously observed MCP-to-REST regression; it will be removed
only after every supported Hermes surface owns discovery through a public API.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
ruff format .
ruff check .
mypy hermes_plugin_tinyfish
pytest --cov=hermes_plugin_tinyfish --cov-fail-under=70
python -m build
```

Live tests are opt-in:

```bash
TINYFISH_LIVE_TESTS=1 TINYFISH_API_KEY=... pytest tests/test_live.py
```

## Maintainer Docs

- [Release operations](docs/operations/release.md)
- [Compatibility testing](docs/operations/compatibility-testing.md)
- [OAuth hardening compatibility report](docs/operations/oauth-hardening-compatibility-report.md)
- [User install smoke test](docs/operations/user-install-smoke-test.md)
- [Hermes extension points](docs/reference/hermes-extension-points.md)
- [TinyFish integration notes](docs/reference/tinyfish-integration.md)
- [Roadmap and non-goals](docs/roadmap.md)

## References

- [TinyFish MCP Integration](https://docs.tinyfish.ai/mcp-integration)
- [TinyFish Authentication](https://docs.tinyfish.ai/authentication)
- [TinyFish Search API](https://docs.tinyfish.ai/search-api)
- [TinyFish Fetch API](https://docs.tinyfish.ai/fetch-api)
- [TinyFish Browser API](https://docs.tinyfish.ai/browser-api)
- [Hermes Web Search Provider Plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/web-search-provider-plugin)
- [Hermes Browser Provider Plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/browser-provider-plugin)
- [Hermes Plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
- [Hermes MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
