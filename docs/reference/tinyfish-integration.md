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

These values are REST fallback defaults only. They do not represent remembered
user intent, and the plugin does not add persistent domain lists, selectors,
or other parity controls. A user can state those requirements in ordinary
language for the current request.

When TinyFish MCP is configured, a `pre_llm_call` hook injects marked routing
guidance when the active context does not already contain that routing version:

- ordinary discovery and page reading use Hermes `web_search` and
  `web_extract`;
- requests needing TinyFish-specific filters, news/research-paper or
  publication-year modes, pagination, selectors, conditional validators,
  output formats, link/image extraction, caching, or timeouts use the native
  TinyFish MCP `search` or `fetch_content` tool exposed by Hermes.

Hermes persists its API-bound message sidecar for prompt-cache replay while
keeping visible conversation content clean. The hook checks only its versioned
marker, so normal replay retains one active copy; if compression removes it,
the next turn injects it again. The hook does not inspect request keywords,
force a tool, or run once per tool call. Hermes remains responsible for
interpreting plain language and choosing among the actual tool schemas. Set
`tinyfish.routing_context: false` to prevent new guidance injections.

`hermes tinyfish usage` reads the authenticated TinyFish wallet endpoint. It
reports available balance, auto-reload state, pending top-ups, and live
per-product contract rates without reading or printing request history.
TinyFish does not document a historical aggregate-spend endpoint. Accounts on
legacy billing, or without a Metronome customer record, receive a documented
wallet-unavailable result and a billing-dashboard link instead of an error or
history dump.

Use `hermes tinyfish doctor --live --transport mcp` to test MCP OAuth without
REST fallback. An explicit `invalid_grant`, authorization challenge, or
invalid/expired-token response is reported as `reauth_required`; a generic
HTTP 400 is deliberately left unclassified. Renew through
`hermes tinyfish reauth`, then reload MCP or restart the affected Hermes
process. The plugin does not treat token-file presence as proof of validity.

Hermes/MCP may wrap the underlying OAuth exception in a task-group exception.
The plugin recursively classifies the bounded nested errors so an explicit
`invalid_grant`, state mismatch, or PKCE mismatch remains `reauth_required`;
the raw exception text is never returned to the user. A generic HTTP 400 stays
`unknown`.

The state parameter remains an opaque security value. The plugin never repairs
or normalizes it. Remote users should remove only whitespace introduced while
copying a visually wrapped authorization URL and must not mix URLs from
different attempts.

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
- Session termination retries documented transient HTTP statuses and transport
  failures at most three times, caps `Retry-After` waits at five seconds, and
  treats 404 as failed cleanup rather than proof of idempotent termination.
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

Plugin loading starts a best-effort update check in a daemon thread. The check
uses GitHub Releases for Hermes Git installs and PyPI metadata for package
installs, accepts stable semantic versions only, and caches the result for 24
hours under the active `HERMES_HOME`. Hermes receives an ephemeral, one-time
per-process notice when the installed version is older. The check never runs
an updater, uses no credentials, and silently tolerates offline or unwritable
environments. Set `tinyfish.update_check: false` or `NO_UPDATE_NOTIFIER=1` to
opt out.

## References

- [TinyFish MCP integration](https://docs.tinyfish.ai/mcp-integration)
- [TinyFish authentication](https://docs.tinyfish.ai/authentication)
- [TinyFish Search API](https://docs.tinyfish.ai/search-api)
- [TinyFish Fetch API](https://docs.tinyfish.ai/fetch-api)
- [TinyFish Browser API](https://docs.tinyfish.ai/browser-api)
- [Hermes MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
