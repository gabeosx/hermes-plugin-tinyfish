# Routing and Update Awareness Release Readiness Report

- Date: 2026-08-04
- Operator: Codex
- Verdict: conditional no-go pending the live release gates below
- Platform: macOS 26.5 arm64
- Local Python: 3.13.14
- Hermes compatibility Python: 3.12.8
- Plugin base: `1f6b46d` (`v0.2.4`) plus the
  `codex/tinyfish-routing-update-awareness` feature changes
- Feature commit: `6d1f302` plus this report update
- Candidate release: `v0.3.0`
- Credentials copied, printed, or changed: none

## Feature Evidence

- The final wheel loaded through the `hermes_agent.plugins` entry point on
  Hermes 0.18.2 and 0.19.0.
- Both Hermes versions selected `tinyfish` for Search and Extract, recognized
  the hosted OAuth MCP configuration, reported diagnostics schema 3, and
  passed non-live Doctor checks.
- The real Hermes hook manager returned one marked routing block for an empty
  context, no block when the marked `api_content` sidecar was replayed, and one
  fresh block after simulated compression removed the marker.
- Hermes's API-sidecar composition retained one routing copy on the next turn,
  added zero new copies on that turn, and kept visible stored user content
  clean.
- No `web-tinyfish` model-callable tools were registered.
- A seeded outdated PyPI install produced the pip-specific update instruction;
  Git installs resolved to `hermes plugins update web-tinyfish`; unknown
  ownership produced no unsafe command.
- A simulated two-second update request left plugin registration and the first
  hook nonblocking.
- Live public GitHub Releases and PyPI metadata returned stable version 0.2.4
  in the formats accepted by the checker.

## Automated Checks

- Ruff formatting and lint: passed.
- Python compilation: passed.
- Strict mypy: passed.
- Pytest: 182 passed, 1 credentialed live test skipped.
- Package coverage: 85%, above the 70% release floor.
- Wheel and source distribution build: passed.
- Wheel archive integrity and installed-wheel smoke checks: passed.
- Git diff whitespace validation and CI YAML parsing: passed.

Protected GitHub CI provided the authoritative Python 3.10, 3.11, 3.12,
and 3.13 matrix results for the feature PR. PR #37 passed all four Python jobs,
dependency review, and the Hermes 0.18.2/0.19.0 compatibility jobs.

## Git Install and Update Gate

A disposable Python 3.12 environment containing Hermes 0.19.0 and no TinyFish
entry-point package installed the plugin from a local Git remote at released
tag `v0.2.1`. Hermes reported source `git` and version 0.2.1. The remote's
`main` branch was then advanced to feature commit `6d1f302`, and
`hermes plugins update web-tinyfish` completed a fast-forward update. Hermes
then reported source `git`, version 0.2.4 (the intentionally unbumped feature
version), GitHub release-channel ownership, TinyFish for Search and Extract,
diagnostics schema 3, and passing non-live status/Doctor checks.

## Release Gates Still Required

The active local Hermes profile has no TinyFish MCP OAuth configuration, token
cache, or REST API-key fallback. The repository has no Actions secret names for
live TinyFish tests. Consequently, this run did not perform:

1. current authenticated MCP-only Search and Fetch;
2. current REST-only Search and Fetch;
3. an explicitly approved paid Browser create/close check; or
4. a gateway restart with sanitized replacement-process logs.

Historical evidence in
[`oauth-hardening-compatibility-report.md`](oauth-hardening-compatibility-report.md)
proves authenticated MCP Search/Fetch and a healthy gateway restart for the
0.2.x provider implementation. It does not replace the current REST, paid
Browser, or candidate-branch gateway gates required by the release runbook.

Do not merge the `release:minor` feature PR while this verdict remains no-go.
After the missing gates pass, update this report to record sanitized results
and change the verdict to go; protected automation may then prepare and publish
`v0.3.0`.
