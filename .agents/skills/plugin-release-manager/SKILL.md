---
name: plugin-release-manager
description: Use this skill for Hermes TinyFish version bumps, changelog updates, release PRs, GitHub Releases, PyPI publishing, tag creation, release workflow verification, and post-release install smoke tests.
---

# Plugin Release Manager

Use this workflow for package and release work. Do not create a package release
for docs-only instruction changes unless the PyPI README or package metadata
needs updating.

## Before editing

1. Check `git status --short` and preserve unrelated user changes.
2. Confirm the current version in:
   - `pyproject.toml`
   - `plugin.yaml`
   - `CHANGELOG.md`
3. Confirm the intended semantic version bump with the user unless it is already
   explicit.

## Version and changelog

- Prefer the Prepare Release GitHub Actions workflow for release PRs. It
  computes the next version, updates `pyproject.toml` and `plugin.yaml`,
  promotes `CHANGELOG.md` `Unreleased` notes into a dated version section, and
  opens the release PR.
- For manual release prep, bump semver consistently in `pyproject.toml` and
  `plugin.yaml`.
- Move relevant `CHANGELOG.md` `Unreleased` notes into a dated release entry.
- Keep release notes concise and user-facing.
- Keep GitHub plugin install/update as the primary Hermes-native path.
- Keep PyPI as a secondary package channel.

## Local verification

Run the full local test/build suite before opening or updating a release PR:

```bash
python3 -m ruff format --check .
python3 -m ruff check .
python3 -m mypy hermes_plugin_tinyfish
python3 -m pytest
rm -rf dist && python3 -m build
```

If integration behavior changed, also use the `hermes-compatibility-tester`
workflow.

## PR and release flow

- Use PR flow for protected `main`.
- After the release PR merges, create an annotated tag like `v0.1.5`.
- Push the tag to trigger the release workflow.
- Verify GitHub Release assets include both wheel and sdist.
- Verify PyPI only after the publish workflow completes and PyPI publishing is
  enabled for the release:

```bash
python3 -m pip index versions hermes-plugin-tinyfish --no-cache-dir
```

Then perform a fresh virtualenv install smoke test.

## Guardrails

- Do not publish a release, create a tag, or push package artifacts unless the
  user explicitly asks.
- Never store or print secrets.
- Report any skipped verification command and why.
