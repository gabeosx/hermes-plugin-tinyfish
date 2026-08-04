# Routing and Update Awareness Release Readiness Report

- Date: 2026-08-04
- Operator: Codex
- Verdict: go
- Platform: macOS 26.5 arm64
- Local Python: 3.13.14
- Hermes compatibility Python: 3.12.8
- Plugin base: `1f6b46d` (`v0.2.4`) plus the
  `codex/tinyfish-routing-update-awareness` feature changes
- Feature commit: `6d1f302` plus release-readiness evidence updates
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

## Live Search/Fetch and Gateway Gates

The candidate temporarily replaced a fully preserved live plugin checkout in
the existing Hermes Docker deployment; no credential file or value was read or
copied. Candidate `hermes tinyfish doctor --live --transport mcp --json`
reported both `live_search_ok: true` and `live_fetch_ok: true` over MCP.
Candidate `--transport rest` reported both checks true over REST. Both runs
kept TinyFish selected for Search and Extract and reported no provider fallback.

The `hermes-gateway` service was restarted with the candidate installed. Its
start timestamp changed from `2026-08-04T13:10:54Z` to
`2026-08-04T18:16:11Z`, it returned healthy, and the gateway container reported
the candidate's diagnostics schema 3 with TinyFish Search/Extract active. The
container emitted no startup or error log lines during the gate.

The pre-test live checkout was dirty, so it was backed up before candidate
installation. After the gate, its exact commit (`16fa31b`) and the same modified
and untracked file set were restored, container ownership was restored, and the
gateway was restarted again. It returned healthy at
`2026-08-04T18:18:18Z`, leaving the deployment in its original code state.

## Paid Browser Gate

After explicit user approval, the candidate performed exactly one
`hermes tinyfish doctor --live-paid --json` run. It reported
`live_paid_ok: true`, `live_paid_browser_ok: true`, and
`live_paid_browser_cleanup_ok: true`, confirming that the Browser session was
created and closed successfully. The diagnostic emitted no session ID,
connection URL, credential, or TinyFish response data.

For the gate only, `browser.cloud_provider` changed from `firecrawl` to
`tinyfish` and `tinyfish.credit_policy.browser` changed from its prior unset
state to `allow`. Immediately afterward, the provider was restored to
`firecrawl`, the policy key was removed to restore its exact prior state, and
the original dirty plugin checkout at commit `16fa31b` was restored with the
same modified and untracked file set. The gateway was restarted again against
that restored state and returned healthy at `2026-08-04T18:29:22Z`.

All required gates have now passed. PR #37 may be marked ready and merged;
protected release automation may prepare and publish `v0.3.0`.
