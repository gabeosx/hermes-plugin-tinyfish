# Roadmap and Non-Goals

The plugin is intentionally narrow: Hermes owns agency, while TinyFish supplies
Search, Fetch, and optional Browser infrastructure.

## Later: Demand-Driven Enhancements

The following areas may be promoted only when user evidence justifies them:

- Search and Fetch normalization, filters, caching, metadata, and diagnostics.
- Browser session reliability, cleanup, observability, and Hermes compatibility.
- Safer setup, migration reporting, and provider-selection verification.

These are directions rather than commitments. Concrete work should begin with
a target user, observed need, expected impact, and acceptance criteria.

## Explicit Non-Goals

- TinyFish Agent execution or run lifecycle management.
- Model-callable TinyFish Agent tools.
- Browser Context Profile or Vault management.
- Agent batch operations, SSE streaming, webhooks, and delegated automation.
- Full TinyFish API or MCP catalog parity.

Users who need excluded TinyFish-native functionality can configure TinyFish's
full MCP service independently in Hermes. Those tools remain outside this
plugin's setup, policy, diagnostics, and compatibility guarantees.
