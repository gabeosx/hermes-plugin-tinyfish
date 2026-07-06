# Hermes TinyFish Plugin

[![CI](https://github.com/gabeosx/hermes-plugin-tinyfish/actions/workflows/ci.yml/badge.svg)](https://github.com/gabeosx/hermes-plugin-tinyfish/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/badge/PyPI-pending-lightgrey.svg)](https://github.com/gabeosx/hermes-plugin-tinyfish/releases)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Security Policy](https://img.shields.io/badge/Security-policy-green.svg)](SECURITY.md)

TinyFish web search and content extraction for [Hermes Agent](https://hermes-agent.nousresearch.com/docs/).

The plugin adds `tinyfish` as a native Hermes `web_search` and `web_extract`
backend. It prefers TinyFish's hosted OAuth MCP server and falls back to direct
REST API calls with `TINYFISH_API_KEY` when MCP OAuth is unavailable.

## Install

Hermes Git plugin install:

```bash
hermes plugins install gabeosx/hermes-plugin-tinyfish --enable
hermes tinyfish setup
```

Hermes' Git plugin installer currently clones the repository default branch.
Stable release artifacts are published on the
[GitHub Releases page](https://github.com/gabeosx/hermes-plugin-tinyfish/releases).

PyPI install is planned after PyPI Trusted Publishing is configured:

```bash
pip install hermes-plugin-tinyfish
hermes plugins enable web-tinyfish
hermes tinyfish setup
```

## What Setup Does

`hermes tinyfish setup` writes ordinary user configuration only:

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
```

It may also save `TINYFISH_API_KEY` to `~/.hermes/.env` if you choose to add
an API-key fallback.

The plugin does not patch Hermes Agent, update scripts, Dockerfiles, or any
files inside a Hermes checkout.

## Verify

```bash
hermes tinyfish doctor
hermes tinyfish doctor --live
```

`doctor --live` performs a real TinyFish search and fetch. It requires either
working MCP OAuth or `TINYFISH_API_KEY`.

## Manual Configuration

OAuth MCP only:

```bash
hermes mcp add tinyfish --url https://agent.tinyfish.ai/mcp --auth oauth
hermes mcp login tinyfish
hermes mcp configure tinyfish
```

Then set:

```yaml
web:
  search_backend: tinyfish
  extract_backend: tinyfish
```

REST fallback only:

```bash
export TINYFISH_API_KEY="..."
```

## Upgrade Safety

This plugin uses public Hermes extension points:

- `ctx.register_web_search_provider(...)`
- `ctx.register_cli_command(...)`
- Hermes MCP config under `mcp_servers`
- Hermes `.env` config helpers for optional API-key fallback

Because it is installed as a user plugin or Python entry point, normal
`hermes update` operations do not overwrite it.

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

## References

- [TinyFish MCP Integration](https://docs.tinyfish.ai/mcp-integration)
- [TinyFish Authentication](https://docs.tinyfish.ai/authentication)
- [TinyFish Search API](https://docs.tinyfish.ai/search-api)
- [TinyFish Fetch API](https://docs.tinyfish.ai/fetch-api)
- [Hermes Web Search Provider Plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/web-search-provider-plugin)
- [Hermes Plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
- [Hermes MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
