---
name: hermes-compatibility-tester
description: Use this skill when verifying the TinyFish plugin against a Hermes install or source checkout, Hermes upgrades, gateway behavior, plugin install or update behavior, MCP OAuth behavior, web provider selection, or whether Hermes is actually using TinyFish instead of another web provider.
---

# Hermes Compatibility Tester

Use this workflow to verify the plugin through Hermes user paths.

## Workspace boundaries

- Treat this repository as the plugin source.
- Prefer the installed `hermes` command for user-path checks.
- If a Hermes source checkout is needed, use `HERMES_SOURCE_ROOT` instead of a
  machine-specific path.
- Avoid modifying Hermes core files.
- Do not store or print secrets such as `TINYFISH_API_KEY` or OAuth tokens.

## Preferred command context

Run Hermes integration commands with the installed Hermes command:

```bash
hermes plugins list
hermes plugins update web-tinyfish
hermes tinyfish status
hermes tinyfish doctor
hermes tinyfish doctor --live
```

If the user specifically wants source-checkout behavior, set
`HERMES_SOURCE_ROOT`, change into that directory, and use the checkout's
documented launcher. Say which command path was used in the report.

## What to verify

- The plugin is installed or updated through the Hermes plugin path.
- Hermes config selects TinyFish:

```yaml
web:
  search_backend: tinyfish
  extract_backend: tinyfish
```

- MCP OAuth is configured for the hosted TinyFish endpoint:

```text
https://agent.tinyfish.ai/mcp
```

- `doctor` passes for local config checks.
- `doctor --live` passes when live credentials are available.
- Hermes is using TinyFish rather than Firecrawl, Tavily, or another provider.
- Gateway restart/load behavior is verified when plugin loading, provider
  registration, or long-running Hermes gateway behavior may be affected.

## Reporting

Report:

- Commands run and whether they passed.
- Whether Hermes selected TinyFish for both search and extract.
- Whether MCP OAuth or REST fallback was used, without exposing tokens.
- Any skipped live checks and the reason.
- Any evidence that Hermes fell back to another provider.
