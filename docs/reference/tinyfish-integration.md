# TinyFish Integration

This independent community plugin integrates TinyFish with Hermes Agent. It is
not affiliated with, endorsed by, or maintained by TinyFish or Hermes / Nous
Research.

Hermes owns reasoning, planning, tool choice, and browser interaction. TinyFish
provides web data and optional remote browser infrastructure.

Pricing and free-use assumptions are based on current TinyFish documentation
only. TinyFish currently describes Search and Fetch as free and Browser as
credit-consuming. Search and Fetch are enabled by setup; Browser remains
policy-denied until the user opts in.

## Capability Map

| TinyFish capability | Hermes surface | Default |
| --- | --- | --- |
| Search | `web_search` provider | Enabled by setup |
| Fetch | `web_extract` provider | Enabled by setup |
| Browser | Hermes `BrowserProvider` named `tinyfish` | Denied |
| Agent and Agent run lifecycle | Not provided | Excluded |
| Browser Context Profiles and Vault | Not provided | Excluded |

## Search and Fetch Routing

Search and Fetch are MCP-first:

- Hosted MCP endpoint: `https://agent.tinyfish.ai/mcp`
- Plugin-managed MCP tools: `search`, `fetch_content`
- REST fallback: `TINYFISH_API_KEY`

REST fallback supports optional TinyFish Search/Fetch configuration:

```yaml
tinyfish:
  search:
    location: US
    language: en
    recency_minutes: 1440
  fetch:
    format: markdown
    ttl: 3600
```

`hermes tinyfish usage` reads Fetch operation history from TinyFish's Fetch
usage endpoint. It does not report Agent or Browser billing.

## Browser Infrastructure

TinyFish Browser can be selected as Hermes's remote browser provider:

```yaml
browser:
  cloud_provider: tinyfish
tinyfish:
  credit_policy:
    browser: request
```

Browser policies are `deny`, `request`, and `allow`. The default is `deny`.
`request` uses Hermes's existing approval flow for each `browser_*` tool
invocation, while `allow` permits Browser tools without per-invocation
approval. The first permitted Browser call creates the remote session when one
does not already exist for the task.

Provider behavior:

- `is_available()` is non-networked and requires an API key plus a non-deny
  Browser policy.
- Hermes owns page-level planning and browser tool calls.
- TinyFish session IDs and connection URLs are not printed by diagnostics.
- `doctor --live-paid` creates and closes one Browser session and treats failed
  cleanup as a failed diagnostic.

## Deliberate Exclusions

TinyFish Agent is a delegated goal-based automation loop. Exposing it through
this plugin would duplicate Hermes's own planning and browser loop and make
tool ownership, approval, and billing less clear. Browser Context Profiles,
Vault, Agent batch operations, Agent SSE, and other delegated-automation
features are excluded with it.

The plugin does not register Agent tools, provide Agent/Profile CLI commands,
or manage remote Agent/Profile state. Users who need those TinyFish-native
capabilities can configure TinyFish's full MCP service independently in Hermes;
that configuration is outside this plugin's setup, policy, diagnostics, and
compatibility guarantees.

The plugin-managed `tinyfish` MCP entry always limits its tool list to
`search` and `fetch_content`.

## Upgrade Behavior

Plugin `0.2.x` configurations may contain `agent`, `profile_setup`, or
`model_tools` under `tinyfish.credit_policy`. These keys are ignored and
reported by `hermes tinyfish status` as `retired_credit_policy_keys`.

Reading status, loading the plugin, and updating it do not mutate user config
or remote TinyFish state. `hermes tinyfish credits reset` is the explicit
migration command: it removes retired keys and restores `browser: deny`.

## References

- [TinyFish MCP integration](https://docs.tinyfish.ai/mcp-integration)
- [TinyFish authentication](https://docs.tinyfish.ai/authentication)
- [TinyFish Search API](https://docs.tinyfish.ai/search-api)
- [TinyFish Fetch API](https://docs.tinyfish.ai/fetch-api)
- [TinyFish Browser API](https://docs.tinyfish.ai/browser-api)
- [Hermes MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
