# Security Policy

## Supported Versions

Security fixes are released for the latest minor version.

## Reporting a Vulnerability

Please report security issues privately by opening a GitHub security advisory
for this repository. Do not disclose vulnerabilities in public issues until a
fix is available.

## Design Notes

- The plugin does not modify Hermes Agent source files.
- The preferred TinyFish authentication path is Hermes' OAuth MCP support.
- API keys are only used as an explicit REST fallback through
  `TINYFISH_API_KEY`.
- `hermes tinyfish status` and `doctor` never print secret values.
- Live tests are opt-in and are not run by default in CI.
