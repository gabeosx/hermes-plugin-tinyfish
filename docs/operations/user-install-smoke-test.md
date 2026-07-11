# User Install Smoke Test

Use this smoke test to verify the experience an outside Hermes user should
have. Use a disposable `HERMES_HOME`, and never print credentials.

## Primary Git Path

```bash
hermes plugins install gabeosx/hermes-plugin-tinyfish --enable
hermes tinyfish setup
hermes tinyfish doctor
hermes tinyfish doctor --live
```

`doctor --live` requires working MCP OAuth or `TINYFISH_API_KEY`. It runs Search
and Fetch independently and must fail when either check fails.

## Expected Configuration

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
    browser: deny
```

If the user chooses REST fallback, setup may save `TINYFISH_API_KEY` in the
Hermes user environment. Do not print its value.

The plugin must identify itself as an independent community plugin. Mentions of
free Search/Fetch reflect current TinyFish documentation rather than a
guarantee.

## Migration Check

When updating a `0.2.x` profile, verify:

```bash
hermes plugins update web-tinyfish
hermes tinyfish status --json
```

Old `agent`, `profile_setup`, and `model_tools` policy keys must appear under
`retired_credit_policy_keys` and remain untouched until the user explicitly
runs:

```bash
hermes tinyfish credits reset
```

After reset, the policy contains only `browser: deny`. The retired `agent` and
`profiles` commands must be rejected, no TinyFish Agent tools may be
registered, and no remote TinyFish state may be modified.

## Optional Browser Check

Browser is the only credit-policy surface:

```bash
hermes tinyfish credits status
hermes tinyfish credits set browser request
hermes tinyfish doctor --live-paid
hermes tinyfish credits reset
```

Obtain explicit approval before the paid check. It must refuse under `deny`,
request approval under `request`, run under `allow` or after approval, and close
the created session without exposing connection details.

## Secondary PyPI Path

```bash
python3 -m pip install hermes-plugin-tinyfish
hermes plugins enable web-tinyfish
hermes tinyfish setup
```

Use this path for package-channel smoke tests. Prefer the GitHub plugin path for
normal Hermes user ergonomics.

## Pass Criteria

- Fresh install and update from `0.2.1` succeed.
- Setup writes ordinary user config only.
- Non-live Doctor passes without credentials or network access.
- Live Doctor passes through MCP-only and REST-only fixtures.
- Hermes resolves both web providers to `tinyfish` with no fallback.
- Status is non-secret and reports retired keys without mutating config.
- Reset leaves only `browser: deny`.
- No TinyFish Agent/Profile commands or model tools are exposed.
- An explicitly approved Browser create/close check passes.
- Gateway restart loads the plugin without import, registration, or stale-tool
  errors.

## References

- [TinyFish MCP integration](https://docs.tinyfish.ai/mcp-integration)
- [TinyFish authentication](https://docs.tinyfish.ai/authentication)
- [Hermes plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
