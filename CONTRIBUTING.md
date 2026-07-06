# Contributing

Contributions are welcome.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
ruff format .
ruff check .
mypy hermes_plugin_tinyfish
pytest
python -m build
```

## Pull Request Expectations

- Include tests for behavior changes.
- Keep the plugin upgrade-safe: do not modify Hermes core files, local update
  scripts, Dockerfiles, or generated user state.
- Do not log or print API keys, OAuth tokens, or MCP token file contents.
- Use TinyFish MCP OAuth first when possible and REST API keys only as fallback.
