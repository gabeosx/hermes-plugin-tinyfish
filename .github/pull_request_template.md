## Summary

## Testing

- [ ] `ruff format --check .`
- [ ] `ruff check .`
- [ ] `mypy hermes_plugin_tinyfish`
- [ ] `pytest`
- [ ] `python -m build`

## Upgrade Safety

- [ ] This change does not modify Hermes core files.
- [ ] This change does not require patching Hermes update scripts.
- [ ] This change does not log TinyFish API keys or MCP tokens.
- [ ] User-facing docs stay clear that this is an independent community plugin.
- [ ] Credit-risking TinyFish Agent, Browser, or Profile changes default to `deny`.
- [ ] Any free/pricing claims are phrased as current understanding from TinyFish docs.
