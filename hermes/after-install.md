# TinyFish for Hermes is installed

Finish setup with:

```bash
hermes tinyfish setup
```

The setup flow prefers TinyFish OAuth, can use `TINYFISH_API_KEY` or the
TinyFish CLI's `MCP_TINYFISH_API_KEY`, and verifies the active transport.

Then check the installation with:

```bash
hermes tinyfish doctor
```

Search and Fetch are free and enabled through Hermes. Paid Browser sessions
remain disabled until you explicitly choose an approval policy during setup.

Documentation: https://github.com/gabeosx/hermes-plugin-tinyfish#readme
