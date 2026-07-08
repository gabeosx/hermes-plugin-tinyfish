# User Install Smoke Test

Use this smoke test to verify the experience an outside Hermes user should have.

## Primary Path

Install and enable the plugin from GitHub:

```bash
hermes plugins install gabeosx/hermes-plugin-tinyfish --enable
```

Run setup:

```bash
hermes tinyfish setup
```

Verify:

```bash
hermes tinyfish doctor
hermes tinyfish doctor --live
```

`doctor --live` requires either working MCP OAuth or `TINYFISH_API_KEY`.
It tests only Search and Fetch.

## Expected Configuration

Setup should configure TinyFish MCP OAuth:

```yaml
mcp_servers:
  tinyfish:
    url: https://agent.tinyfish.ai/mcp
    auth: oauth
    tools:
      include: [search, fetch_content]
      resources: false
      prompts: false

web:
  search_backend: tinyfish
  extract_backend: tinyfish

tinyfish:
  credit_policy:
    agent: deny
    browser: deny
    profile_setup: deny
    model_tools: deny
```

If the user chooses REST fallback, setup may save `TINYFISH_API_KEY` in the
Hermes user environment. Do not print the value.

The plugin must present itself as an independent community plugin, unaffiliated
with TinyFish or Hermes / Nous Research. Any mention of free Search/Fetch
should be phrased as current understanding from TinyFish documentation, not a
guarantee.

## Credit Policy Smoke Check

Verify default-deny policy:

```bash
hermes tinyfish credits status
```

Optional credit-risking checks should only run after an explicit policy change:

```bash
hermes tinyfish credits set browser request
hermes tinyfish doctor --live-paid
hermes tinyfish credits reset
```

`doctor --live-paid` must refuse under `deny`, request approval under
`request`, and run only under `allow` or after approval.

## Secondary PyPI Path

PyPI is available for environments that load `hermes_agent.plugins` entry
points:

```bash
python3 -m pip install hermes-plugin-tinyfish
hermes tinyfish setup
```

Use this path for package-channel smoke tests, but prefer the GitHub plugin path
when validating normal Hermes user ergonomics.

## Pass Criteria

- Plugin install or update succeeds.
- `hermes tinyfish setup` writes ordinary user config only.
- `hermes tinyfish doctor` passes.
- `hermes tinyfish doctor --live` passes when live credentials are available.
- Hermes selects `tinyfish` for both `web.search_backend` and
  `web.extract_backend`.
- Credit-risking features remain denied after default setup.
- Browser/Agent/Profile commands explain credit policy when blocked.

## References

- [TinyFish MCP integration](https://docs.tinyfish.ai/mcp-integration)
- [TinyFish authentication](https://docs.tinyfish.ai/authentication)
- [Hermes plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
