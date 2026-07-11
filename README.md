# Hermes TinyFish Plugin

[![CI](https://github.com/gabeosx/hermes-plugin-tinyfish/actions/workflows/ci.yml/badge.svg)](https://github.com/gabeosx/hermes-plugin-tinyfish/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/hermes-plugin-tinyfish.svg)](https://pypi.org/project/hermes-plugin-tinyfish/)
[![Python](https://img.shields.io/pypi/pyversions/hermes-plugin-tinyfish.svg)](https://pypi.org/project/hermes-plugin-tinyfish/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Security Policy](https://img.shields.io/badge/Security-policy-green.svg)](SECURITY.md)

TinyFish Search and Fetch providers, plus optional TinyFish Browser
infrastructure, for
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
    browser: deny
```

The plugin prefers TinyFish's hosted OAuth MCP server and falls back to REST
with `TINYFISH_API_KEY` when MCP OAuth is unavailable. It may save
`TINYFISH_API_KEY` to `~/.hermes/.env` if you choose API-key fallback.

Verify Search and Fetch:

```bash
hermes tinyfish doctor
hermes tinyfish doctor --live
```

`doctor --live` runs independent Search and Fetch checks and exits nonzero if
either fails.

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
REST fallback calls.

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
hermes tinyfish doctor --live-paid
```

- `status` is non-secret and reports ignored `0.2.x` policy keys under
  `retired_credit_policy_keys`.
- `usage` reads TinyFish Fetch operation history; it is not Agent or Browser
  billing data.
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
- `ctx.register_cli_command(...)`
- Hermes MCP configuration under `mcp_servers`
- Hermes environment helpers for optional API-key fallback

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
