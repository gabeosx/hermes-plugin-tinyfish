# TinyFish Integration

This independent community plugin integrates TinyFish with Hermes Agent. It is
not affiliated with, endorsed by, or maintained by TinyFish or Hermes / Nous
Research.

Pricing and free-use assumptions are based on current TinyFish documentation
only. TinyFish docs currently describe Search and Fetch as free, while Agent
and Browser use credits. The plugin therefore defaults to Search/Fetch and
denies credit-risking features unless the user changes policy.

## Capability Map

| TinyFish capability | Hermes surface | Default |
| --- | --- | --- |
| Search | `web_search` provider | Enabled by setup |
| Fetch | `web_extract` provider | Enabled by setup |
| Browser | Hermes `BrowserProvider` named `tinyfish` | Denied |
| Agent | CLI commands and optional model tools | Denied |
| Browser Context Profiles | CLI commands | Denied for setup sessions |

## Routing

Search and Fetch remain MCP-first:

- Hosted MCP endpoint: `https://agent.tinyfish.ai/mcp`
- MCP tools: `search`, `fetch_content`
- REST fallback: `TINYFISH_API_KEY`

REST fallback supports optional TinyFish Search/Fetch config under:

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

## Credit Policy

Credit-risking features are controlled by:

```yaml
tinyfish:
  credit_policy:
    agent: deny
    browser: deny
    profile_setup: deny
    model_tools: deny
```

Policies:

- `deny`: fail closed.
- `request`: use Hermes' existing approval gate for each invocation.
- `allow`: run without per-invocation approval.

CLI:

```bash
hermes tinyfish credits status
hermes tinyfish credits set agent request
hermes tinyfish credits set browser allow
hermes tinyfish credits reset
```

## Agent, Browser, and Profiles

Agent commands:

```bash
hermes tinyfish agent run --url https://example.com --goal "Extract pricing"
hermes tinyfish agent run-async --url https://example.com --goal "Extract products"
hermes tinyfish agent status <run_id>
hermes tinyfish agent cancel <run_id>
```

Browser provider selection:

```yaml
browser:
  cloud_provider: tinyfish
tinyfish:
  credit_policy:
    browser: request
```

Profile commands:

```bash
hermes tinyfish profiles list
hermes tinyfish profiles create --name "Example"
hermes tinyfish profiles setup-session <profile_id>
hermes tinyfish profiles save-setup <profile_id> --session-id <session_id>
```

## Provider Semantics

- `is_available()` stays non-networked.
- Search and Fetch normalize TinyFish payloads into Hermes web provider shapes.
- Browser provider availability requires `TINYFISH_API_KEY` and browser policy
  set to `request` or `allow`.
- Optional model-callable Agent tools are registered only when `model_tools` is
  `request` or `allow`.
- Live network verification belongs in `hermes tinyfish doctor --live` or
  `--live-paid`, not provider availability checks.

## References

- [TinyFish MCP integration](https://docs.tinyfish.ai/mcp-integration)
- [TinyFish authentication](https://docs.tinyfish.ai/authentication)
- [TinyFish Search API](https://docs.tinyfish.ai/search-api)
- [TinyFish Fetch API](https://docs.tinyfish.ai/fetch-api)
- [TinyFish Agent API](https://docs.tinyfish.ai/agent-api)
- [TinyFish Browser API](https://docs.tinyfish.ai/browser-api)
- [TinyFish Browser Context Profiles](https://docs.tinyfish.ai/agent-api/browser-context-profiles)
