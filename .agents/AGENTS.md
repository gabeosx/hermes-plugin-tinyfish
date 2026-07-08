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
python3 -m mypy hermes_plugin_tinyfish
python3 -m pytest
python3 -m build
```

Never store or print secrets such as `TINYFISH_API_KEY` or OAuth tokens.
