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
- CLI registration through `ctx.register_cli_command(...)`.
- MCP server configuration under Hermes `mcp_servers`.
- Optional API-key fallback through Hermes environment helpers and
  `TINYFISH_API_KEY`.

The plugin does not call `ctx.register_tool(...)`: Hermes is the agent, and no
TinyFish Agent tools are model-callable through this plugin.

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

Users may set Browser to `request` for Hermes approval on each `browser_*` tool
invocation or `allow` for blanket approval.

## Runtime Discovery

Hermes currently supports runtime plugin discovery. It does not provide a full
public marketplace/search index for this plugin, so installation docs use the
repository identifier directly:

```bash
hermes plugins install gabeosx/hermes-plugin-tinyfish --enable
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
