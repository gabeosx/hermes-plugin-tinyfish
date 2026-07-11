## Summary

<!-- What user or maintainer outcome does this change deliver? -->

## Validation

- [ ] `ruff format --check .`
- [ ] `ruff check .`
- [ ] `python -m compileall hermes_plugin_tinyfish scripts tests`
- [ ] `mypy hermes_plugin_tinyfish`
- [ ] `pytest --cov=hermes_plugin_tinyfish --cov-fail-under=70`
- [ ] `python -m build`
- [ ] Relevant Hermes install/update, provider, or gateway path checked
- [ ] Skipped checks and reasons documented below

## Compatibility and Safety

- [ ] This change uses public Hermes extension points and does not patch Hermes
      core or update scripts.
- [ ] Python 3.10 compatibility is preserved; newer syntax, standard-library
      APIs, and typing features have fallbacks or guards.
- [ ] No TinyFish API keys, OAuth tokens, session IDs, CDP URLs, or signed URLs
      are logged or committed.
- [ ] Search/Fetch remain MCP-first, and the plugin-managed MCP allowlist remains
      restricted to `search` and `fetch_content`.
- [ ] TinyFish Browser remains optional and defaults to `deny`.
- [ ] This change does not add TinyFish Agent/Profile/Vault/delegated-automation
      surfaces or modify remote TinyFish state.
- [ ] User-facing behavior and migration changes include documentation and
      changelog updates.
- [ ] Pricing/free-use language is attributed to current TinyFish documentation
      and is not presented as a guarantee.
- [ ] The plugin remains described as an independent community project.

## Release

<!-- Apply exactly one label when appropriate: release:none/patch/minor/major. -->

Release label: `release:none`

## Notes / Skipped Checks
