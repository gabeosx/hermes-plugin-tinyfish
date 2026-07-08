# Hermes TinyFish Plugin

[![CI](https://github.com/gabeosx/hermes-plugin-tinyfish/actions/workflows/ci.yml/badge.svg)](https://github.com/gabeosx/hermes-plugin-tinyfish/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/hermes-plugin-tinyfish.svg)](https://pypi.org/project/hermes-plugin-tinyfish/)
[![Python](https://img.shields.io/pypi/pyversions/hermes-plugin-tinyfish.svg)](https://pypi.org/project/hermes-plugin-tinyfish/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Security Policy](https://img.shields.io/badge/Security-policy-green.svg)](SECURITY.md)

TinyFish web search, content extraction, and optional credit-gated web
automation for [Hermes Agent](https://hermes-agent.nousresearch.com/docs/).

This is an independent community plugin. It is not affiliated with, endorsed
by, or maintained by TinyFish or Hermes / Nous Research.

TinyFish documentation currently describes Search and Fetch as free, and Agent
and Browser as credit-consuming. This plugin treats Search and Fetch as the
safe default entry point, but pricing and free-use assumptions are based only
on current TinyFish docs and may change. Credit-risking features default to
`deny`.

## Install

Hermes Git plugin install:

```bash
hermes plugins install gabeosx/hermes-plugin-tinyfish --enable
hermes tinyfish setup
```

Python package install:

```bash
pip install hermes-plugin-tinyfish
hermes tinyfish setup
```

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
  credit_policy:
    agent: deny
    browser: deny
    profile_setup: deny
    model_tools: deny
```

The plugin prefers TinyFish's hosted OAuth MCP server and falls back to REST
with `TINYFISH_API_KEY` when MCP OAuth is unavailable. It may save
`TINYFISH_API_KEY` to `~/.hermes/.env` if you choose to add API-key fallback.

Verify the default Search/Fetch setup:

```bash
hermes tinyfish doctor
hermes tinyfish doctor --live
```

`doctor --live` performs only Search and Fetch checks.

## Credit Policy

Credit-risking TinyFish capabilities are controlled independently:

```bash
hermes tinyfish credits status
hermes tinyfish credits set agent request
hermes tinyfish credits set browser allow
hermes tinyfish credits set profile-setup deny
hermes tinyfish credits set model-tools request
hermes tinyfish credits reset
```

Policies:

- `deny`: fail closed. This is the default.
- `request`: use Hermes' existing approval flow for each invocation.
- `allow`: run without per-invocation approval.

`model-tools` controls whether model-callable TinyFish Agent tools are exposed.
Even when `model-tools` is enabled, `agent` must also be set to `request` or
`allow`.

## Optional Capabilities

### Browser Provider

TinyFish Browser can be selected as a Hermes cloud browser provider after
explicit opt-in:

```yaml
browser:
  cloud_provider: tinyfish
tinyfish:
  credit_policy:
    browser: request
```

When selected, TinyFish-backed `browser_*` calls are gated by the browser
credit policy.

### Agent API

Run TinyFish goal-based automation from the CLI:

```bash
hermes tinyfish credits set agent request
hermes tinyfish agent run --url https://example.com --goal "Find the pricing"
hermes tinyfish agent run-async --url https://example.com --goal "Extract product names"
hermes tinyfish agent status <run_id>
hermes tinyfish agent cancel <run_id>
```

### Browser Context Profiles

Manage persistent TinyFish Browser Context Profiles:

```bash
hermes tinyfish profiles list
hermes tinyfish profiles create --name "Example account"
hermes tinyfish credits set profile-setup request
hermes tinyfish profiles setup-session <profile_id>
hermes tinyfish profiles save-setup <profile_id> --session-id <session_id>
hermes tinyfish profiles cancel-setup <profile_id> --session-id <session_id>
```

### Search and Fetch Options

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

MCP remains the preferred path when configured. These options apply to REST
fallback calls.

## Diagnostics

```bash
hermes tinyfish status
hermes tinyfish usage
hermes tinyfish doctor --live
hermes tinyfish doctor --live-paid
```

`doctor --live-paid` respects credit policy. It refuses under `deny`, prompts
under `request`, and runs under `allow`.

## Upgrade Safety

This plugin uses public Hermes extension points:

- `ctx.register_web_search_provider(...)`
- `ctx.register_browser_provider(...)`
- `ctx.register_tool(...)` for optional Agent tools
- `ctx.register_hook("pre_tool_call", ...)` for credit policy gates
- `ctx.register_cli_command(...)`
- Hermes MCP config under `mcp_servers`
- Hermes `.env` config helpers for optional API-key fallback

It does not patch Hermes Agent, update scripts, Dockerfiles, or files inside a
Hermes installation or source checkout.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
ruff format .
ruff check .
mypy hermes_plugin_tinyfish
pytest
python -m build
```

Live tests are opt-in:

```bash
TINYFISH_LIVE_TESTS=1 TINYFISH_API_KEY=... pytest tests/test_live.py
```

## Maintainer Docs

- [Release operations](docs/operations/release.md)
- [Compatibility testing](docs/operations/compatibility-testing.md)
- [User install smoke test](docs/operations/user-install-smoke-test.md)
- [Hermes extension points](docs/reference/hermes-extension-points.md)
- [TinyFish integration notes](docs/reference/tinyfish-integration.md)

## References

- [TinyFish MCP Integration](https://docs.tinyfish.ai/mcp-integration)
- [TinyFish Authentication](https://docs.tinyfish.ai/authentication)
- [TinyFish Search API](https://docs.tinyfish.ai/search-api)
- [TinyFish Fetch API](https://docs.tinyfish.ai/fetch-api)
- [TinyFish Agent API](https://docs.tinyfish.ai/agent-api)
- [TinyFish Browser API](https://docs.tinyfish.ai/browser-api)
- [TinyFish Browser Context Profiles](https://docs.tinyfish.ai/agent-api/browser-context-profiles)
- [Hermes Web Search Provider Plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/web-search-provider-plugin)
- [Hermes Browser Provider Plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/browser-provider-plugin)
- [Hermes Plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
- [Hermes MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
