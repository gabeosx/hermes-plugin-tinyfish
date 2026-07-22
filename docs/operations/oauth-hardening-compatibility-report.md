# OAuth Hardening Compatibility Report

- Date: 2026-07-21
- Operator: Codex
- Platform: Darwin 25.5.0 arm64
- Python: 3.12.8
- Plugin source: `16fa31b` plus the working-tree OAuth hardening changes
- Plugin package version: 0.2.1 (release version intentionally unchanged)
- Install path: freshly built wheel in disposable virtual environments
- Hermes homes: disposable temporary directories for version checks, followed
  by one explicitly authorized local recovery check; no credentials copied

## Automated and Unit Checks

- MCP-first calls with pre-registered tools: passed.
- Lazy MCP discovery before REST fallback: passed.
- Failed discovery followed by configured REST fallback: passed.
- Injected public `ctx.dispatch_tool` path: passed.
- Explicit OAuth reauthorization classification and redaction: passed.
- Explicit OAuth classification through a nested task-group error: passed.
- State/PKCE mismatch classification without weakening validation: passed.
- Generic HTTP 400 remains unclassified: passed.
- MCP-only mode refuses REST fallback: passed.
- REST-only mode skips MCP: passed.
- Reauthorization exit-code and reload guidance: passed.
- CLI nonzero diagnostic status propagation: passed.

## Installed Hermes Checks

Hermes 0.18.2 and 0.19.0 both passed the following user paths with isolated
configuration:

```text
hermes plugins enable web-tinyfish
hermes tinyfish setup --yes --skip-login
hermes tinyfish status --json
hermes tinyfish doctor --json
hermes tinyfish --help
```

Both versions selected `tinyfish` for Search and Extract, returned diagnostics
schema 2, described token-cache presence as non-authoritative, exposed the
`reauth` command, and passed non-live doctor checks. No other web provider was
selected.

On Hermes 0.19.0, an MCP-only live check in an isolated home with no OAuth
credentials returned `mcp_unavailable`, `ok: false`, no REST transport, and
process exit status 1. Output contained no credentials or raw OAuth response.

## Removal-Gate Result

The private lazy-discovery compatibility shim was **not removed**. The offline
installed-package checks cannot prove:

- authenticated Search and Fetch through public dispatch on every surface;
- `/reload-mcp` recovery after a genuinely parked OAuth server;
- TUI and gateway behavior with real TinyFish OAuth; or
- safety under overlapping gateway and CLI refresh attempts.

Those checks require a disposable authorized account or a safe host-level test
fixture. No user token files were read, copied, deleted, or changed. Because the
gate is incomplete and the historical lazy-discovery regression remains valid,
the implementation preserves the existing shim and documents the missing
server-scoped public Hermes API.

## Authorized Local Recovery Check

After the isolated checks, an explicitly authorized recovery test was run
against the user's local Hermes deployment with the gateway and its host
watchdog paused. No token, authorization URL, callback code, or raw OAuth
response was read into this report.

The first headless attempt proved that Hermes correctly rejects a callback
whose opaque state value differs from the authorization request. Hermes then
treated the task-group-wrapped OAuth failure as an ordinary initial connection
failure, launched three additional attempts, and produced callback-port
collisions. This is a host retry/classification defect; the plugin must not
weaken the state check or patch Hermes internals.

A subsequent single flow using whitespace-only cleanup for the visually
wrapped URL succeeded. The MCP-only doctor passed independent Search and Fetch
checks over MCP. After the gateway restarted, multiple Hermes processes noticed
the new token-file revision and registered `mcp__tinyfish__search` and
`mcp__tinyfish__fetch_content`. The gateway became healthy with zero restarts,
and the host watchdog was restored.

This live result proves that Hermes's persisted-token revision reload works in
the tested deployment. It does not prove cross-process refresh rotation is
serialized, nor does it satisfy the full private-shim removal gate across all
supported Hermes versions and surfaces.

## Skipped Checks

- Concurrent refresh reproduction: skipped because it requires controlled
  rotating refresh credentials and belongs to host-level OAuth testing.
- TinyFish Browser paid check: unrelated to this change and requires explicit
  credit approval.
