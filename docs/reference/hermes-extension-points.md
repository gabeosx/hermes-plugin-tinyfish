# Hermes Extension Points

This plugin remains upgrade-safe by using public Hermes extension points
instead of modifying Hermes core.

## Used by This Plugin

- Plugin registration through `hermes_agent.plugins` package entry points and
  Hermes Git plugin install/update.
- Web provider registration through `ctx.register_web_search_provider(...)`.
- Browser provider registration through `ctx.register_browser_provider(...)`.
- Browser credit policy enforcement through
  `ctx.register_hook("pre_tool_call", ...)` and Hermes approval directives.
- Ephemeral routing and maintenance context through
  `ctx.register_hook("pre_llm_call", ...)`.
- CLI registration through `ctx.register_cli_command(...)`.
- In-session diagnostics through `ctx.register_command(...)`.
- Registered MCP tool invocation through `ctx.dispatch_tool(...)`.
- MCP server configuration under Hermes `mcp_servers`.
- Optional API-key fallback through Hermes environment helpers and
  `TINYFISH_API_KEY`.

The plugin does not call `ctx.register_tool(...)`: Hermes is the agent, and no
TinyFish Agent tools are model-callable through this plugin.

## Turn Context

Hermes invokes `pre_llm_call` once before a user turn's LLM loop. The plugin
uses the hook to explain when generic web tools are sufficient and when native
TinyFish MCP schemas are needed. It may also append one cached update notice.
Hermes adds this context to the API-bound user message without changing its
clean stored `content`. Hermes persists an `api_content` sidecar so later turns
can replay the exact prompt-cache prefix; the sidecar can therefore remain in
the model context even though it is absent from visible conversation text.

The routing block carries a versioned marker. The hook checks only that marker
in Hermes-provided history and injects the block when it is missing. Normal
sidecar replay therefore keeps one copy in the active context; compression
that removes it causes reinjection on the next turn. Multiple tool calls do not
invoke the hook again. The plugin re-reads configuration each turn, does not
inspect request keywords, dispatch tools from the hook, or override Hermes's
tool choice. It is active only for the plugin-managed OAuth MCP endpoint and
new injection can be disabled with `tinyfish.routing_context: false`.

The update checker is separate from provider availability. It runs in a daemon
thread, caches only release channel/version/timestamp data under the active
Hermes profile, and never makes status or `is_available()` networked. It does
not use private Hermes update APIs or execute an update command.

## MCP Discovery Compatibility Shim

Hermes does not currently expose a targeted public API for a plugin to query,
discover, reconnect, or read structured health for one configured MCP server.
The plugin therefore retains its pre-existing lazy-discovery shim when the
TinyFish tools are missing. The shim is non-interactive, but Hermes's discovery
function considers every missing configured MCP server, not only TinyFish.
Plugin-triggered discovery is single-flight within one process, and a live
diagnostic gives Search one discovery opportunity rather than immediately
retrying discovery again for Fetch. These guards reduce plugin-created retry
pressure but do not coordinate OAuth refresh across separate Hermes processes.

Do not expand this private dependency. Remove it only after CLI, TUI, gateway,
and diagnostics prove that Hermes-owned startup plus `ctx.dispatch_tool(...)`
preserve MCP-first Search and Fetch across the supported Hermes versions. The
requested public host surface is documented in
[`hermes-mcp-api-gap.md`](hermes-mcp-api-gap.md).

## User Configuration

The plugin writes ordinary user configuration only. It does not edit Hermes
source files, Dockerfiles, update scripts, or bundled provider code.

Expected web provider selection:

```yaml
web:
  search_backend: tinyfish
  extract_backend: tinyfish
```

Expected plugin-managed MCP server:

```yaml
mcp_servers:
  tinyfish:
    url: https://agent.tinyfish.ai/mcp
    auth: oauth
    tools:
      include: [search, fetch_content]
      resources: false
      prompts: false
```

TinyFish Browser is credit-risking and denied by default:

```yaml
tinyfish:
  credit_policy:
    browser: deny
```

Optional default-on context features:

```yaml
tinyfish:
  routing_context: true
  update_check: true
```

Users may set Browser to `request` for Hermes approval on each `browser_*` tool
invocation or `allow` for blanket approval.

## Runtime Discovery

Hermes currently supports runtime plugin discovery. It does not provide a full
public marketplace/search index for this plugin, so installation docs use the
repository identifier directly:

```bash
hermes plugins install gabeosx/hermes-plugin-tinyfish/hermes --enable
```

## Compatibility Rule

If Hermes changes an extension point, adapt this plugin to the new public
plugin/provider/CLI/MCP/config surface. Do not patch Hermes core to preserve old
plugin behavior.

## References

- [Hermes web search provider plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/web-search-provider-plugin)
- [Hermes browser provider plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/browser-provider-plugin)
- [Hermes plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
- [Hermes MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
