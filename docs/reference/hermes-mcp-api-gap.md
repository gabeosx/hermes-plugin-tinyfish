# Hermes MCP Plugin API Gap

The TinyFish plugin can register providers and commands and dispatch already
registered tools through public Hermes APIs. Hermes does not currently expose a
public plugin API scoped to one configured MCP server for:

- checking structured connection and OAuth state;
- discovering or reconnecting only that server;
- reloading it after interactive reauthorization; or
- coordinating refresh-token rotation across Hermes processes.

The supported CLI path also currently lacks a structured reauthorization
result that plugins can consume. Observed Hermes behavior can print an OAuth
failure and still return shell status 0.

## Why This Matters

The plugin's existing lazy-discovery compatibility shim calls Hermes's global
MCP discovery when TinyFish tools are absent. That preserves MCP-first routing,
but discovery may attempt every missing configured MCP server and may overlap
with discovery in a gateway or another CLI process. Removing the shim without
a replacement reintroduces the previously fixed behavior where TinyFish falls
through to REST before its MCP tools are registered.

## Requested Public Surface

A future public `PluginContext` MCP API should provide server-scoped operations
equivalent to:

```text
get_mcp_server_status(name) -> structured non-secret state
ensure_mcp_server_connected(name, interactive=False) -> structured result
reload_mcp_server(name) -> structured result
```

The host should own token storage, atomic persistence, refresh coordination,
and retry policy. Results should distinguish at least `connected`,
`not_configured`, `auth_required`, `connecting`, `parked`, and `service_error`
without returning credentials or raw authorization payloads.

Host retry policy should unwrap task-group/exception-group errors before
classification. Explicit OAuth failures such as `invalid_grant`, state
mismatch, PKCE mismatch, and interactive authorization requirements should be
terminal for that connection attempt: they must not consume ordinary network
retry budgets or launch additional browser flows. Any legitimate retry must
fully close the prior callback listener before binding again. The CLI should
return nonzero when reauthorization fails.

Startup should expose `auth_required`/`needs_reauth` distinctly from
`connecting`, `unreachable`, or `parked`, allowing the host to notify the user
once without repeatedly probing the network.

The host's existing token-file revision watch was verified to work after a
successful TinyFish reauthorization: independent doctor, gateway, and health
processes noticed the new file revision and registered both TinyFish tools.
The requested API should preserve that behavior; it does not justify plugin
token polling or token-file locking.

## Removal Gate

Until such an API exists, remove the compatibility shim only if the minimum and
latest supported Hermes releases prove that CLI, TUI, gateway, and diagnostic
entry points all complete host-owned discovery before TinyFish provider calls,
public tool dispatch reaches Search and Fetch, and `/reload-mcp` recovers a
parked server. No Hermes source modification is part of this plugin.
