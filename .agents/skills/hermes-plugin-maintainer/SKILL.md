---
name: hermes-plugin-maintainer
description: Use this skill when changing Hermes TinyFish plugin implementation, provider behavior, REST or MCP routing, setup CLI behavior, normalization, tests, package metadata, or README usage docs. Also use it for small maintenance changes that can affect packaging, plugin registration, or user-facing Hermes behavior.
---

# Hermes Plugin Maintainer

Use this workflow for normal maintenance of the standalone TinyFish provider
plugin.

## First checks

1. Read `AGENTS.md` and `.agents/AGENTS.md`.
2. Inspect the files relevant to the requested change before editing.
3. Check `git status --short` and preserve unrelated user changes.
4. Keep changes inside this plugin repository unless the user explicitly asks
   otherwise.

## Design constraints

- Treat any separate Hermes source checkout as reference and integration-test
  context only.
- Do not patch, vendor, or depend on Hermes core files for normal plugin
  behavior.
- Preserve Hermes upgrade safety by using public plugin, provider, CLI, MCP,
  and config extension points.
- Keep GitHub plugin install/update as the primary Hermes-native user path.
- Keep PyPI as a secondary package channel.

## TinyFish routing constraints

Preserve MCP-first behavior:

- Prefer TinyFish MCP tools before REST.
- Fall back to REST only when `TINYFISH_API_KEY` is configured.
- Keep `is_available()` non-networked; availability checks must not perform live
  TinyFish or Hermes calls.
- Never store or print secrets such as `TINYFISH_API_KEY` or OAuth tokens.

## Implementation workflow

1. Make the narrowest change that fits the existing package structure.
2. Add or update focused tests for behavior changes.
3. Update README or docs when user-facing commands, behavior, config, or
   release process changes.
4. If integration behavior may be affected, use or recommend the
   `hermes-compatibility-tester` skill.

## Verification

Run the full local suite unless the user explicitly narrows the task or an
environment blocker prevents it:

```bash
python3 -m ruff format --check .
python3 -m ruff check .
python3 -m mypy hermes_plugin_tinyfish
python3 -m pytest
python3 -m build
```

For docs-only changes, still run at least:

```bash
python3 -m pytest
python3 -m build
```

Report any command that was not run and why.
