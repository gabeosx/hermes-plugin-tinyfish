# TinyFish for Hermes has moved to a minimal install surface

This compatibility entry point keeps existing installations working. For
future scanner-clean updates, reinstall from the dedicated subdirectory:

```bash
hermes plugins install gabeosx/hermes-plugin-tinyfish/hermes --force --enable
hermes tinyfish setup
```

The reinstall preserves your Hermes configuration, OAuth state, and externally
managed API keys.
