# Hermes TinyFish Plugin Agent Instructions

This is the standalone TinyFish web provider plugin for Hermes Agent.

Optional local workspace:

- `HERMES_PLUGIN_TINYFISH_ROOT` may point at this plugin checkout.
- `HERMES_SOURCE_ROOT` may point at a separate Hermes source checkout used for
  reference and integration checks.
- If these variables are not set, infer the plugin root from the current
  repository and use the installed `hermes` command for user-path checks.

## Repository boundaries

- Keep TinyFish integration changes in this plugin repository.
- Treat any separate Hermes source checkout as reference and integration-test
  context only.
- Do not move this plugin into Hermes.
- Do not patch, vendor, or depend on local Hermes core files for normal plugin
  behavior.
- Preserve upgrade safety by using Hermes plugin, provider, CLI, MCP, and config
  extension points.

## Python compatibility

- Python 3.10 is the compatibility floor because `pyproject.toml` declares
  `requires-python = ">=3.10"`.
- Do not use syntax, standard-library modules, or typing features introduced
  after Python 3.10 unless the code has a Python 3.10 fallback or guard.
- Common examples:
  - Use `tomllib` only behind a `tomli` fallback.
  - Avoid `except*`, exception groups, and other Python 3.11+ syntax.
  - Avoid Python 3.11+ typing syntax unless it is compatible with Python 3.10
    under `from __future__ import annotations` and current tooling.
- Run or rely on the CI matrix for Python 3.10, 3.11, 3.12, and 3.13 before
  merging.

## Skill routing

Before substantive work, inspect `.agents/skills/` and use the most specific
matching project skill:

- `hermes-plugin-maintainer`: implementation, provider behavior, REST/MCP
  routing, setup CLI, normalization, tests, package metadata, and README usage
  docs.
- `hermes-compatibility-tester`: Hermes integration checks, gateway
  behavior, plugin install/update behavior, MCP OAuth behavior, and provider
  selection checks.
- `plugin-release-manager`: version bumps, changelog updates, release PRs,
  GitHub Releases, PyPI publishing, and post-release verification.
- `skill-creator`: creation or maintenance of project skills.

Prefer the most specific matching skill over reconstructing workflow from
memory.

## User-path testing

Prefer real user-path testing when behavior may be affected:

```bash
hermes plugins install gabeosx/hermes-plugin-tinyfish --enable
hermes tinyfish setup
hermes tinyfish doctor --live
```

For local integration checks with an installed Hermes command:

```bash
hermes plugins list
hermes plugins update web-tinyfish
hermes tinyfish status
hermes tinyfish doctor
hermes tinyfish doctor --live
```

For checks against a source checkout, set `HERMES_SOURCE_ROOT` and use that
checkout's documented development launcher. Do not assume a particular wrapper
script layout.

```bash
cd "$HERMES_SOURCE_ROOT"
hermes plugins list
hermes tinyfish status
```

Check gateway restart/load behavior when plugin loading or provider registration
changes.

## Core-only product scope

- Keep TinyFish Search and Fetch as Hermes `web_search` and `web_extract`
  providers with MCP-first routing.
- Keep TinyFish Browser optional, default-deny, and controlled through Hermes's
  own browser/agent loop.
- Do not add TinyFish Agent tools, Agent/Profile CLI commands, Browser Context
  Profile management, Vault, batch/SSE, or other delegated automation to this
  plugin. Hermes already owns planning and browser interaction.
- Users needing excluded TinyFish-native features may configure the full
  TinyFish MCP service independently; that surface is outside this plugin's
  setup, policy, diagnostics, and compatibility guarantees.

## Release policy

- Use GitHub Releases for public versions.
- Keep `pyproject.toml`, `plugin.yaml`, and `CHANGELOG.md` versions aligned for
  releases.
- Keep PyPI as a secondary package channel.
- The Hermes-native user path is GitHub plugin install/update.
- Do not publish a release, create a tag, or push package artifacts unless the
  user explicitly asks.

## Validation

Useful local verification:

```bash
python3 -m ruff format --check .
python3 -m ruff check .
python3 -m compileall hermes_plugin_tinyfish scripts tests
python3 -m mypy hermes_plugin_tinyfish
python3 -m pytest
python3 -m build
```

Never store or print secrets such as `TINYFISH_API_KEY` or OAuth tokens.
