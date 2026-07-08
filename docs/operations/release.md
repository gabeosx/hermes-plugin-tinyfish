# Release Operations

Use this runbook when preparing a public Hermes TinyFish plugin release.

## Channels

GitHub Releases are the primary public release channel for Hermes users.

PyPI exists as a secondary package channel for environments that load
`hermes_agent.plugins` entry points, but Hermes Git plugin install is the more
ergonomic user path:

```bash
hermes plugins install gabeosx/hermes-plugin-tinyfish --enable
```

Do not create a package release for docs-only instruction changes unless the
PyPI README or package metadata needs updating.

## Preflight

Check the working tree before editing:

```bash
git status --short
```

Confirm the current version in:

- `pyproject.toml`
- `plugin.yaml`
- `CHANGELOG.md`

Then choose the intended semantic version bump.

## Prepare the Release PR

Use the **Prepare Release** GitHub Actions workflow for normal releases. Choose
a `patch`, `minor`, or `major` bump, or pass an explicit version such as
`0.2.0`.

The workflow:

- computes the next version when only a bump is supplied;
- updates `pyproject.toml`;
- updates `plugin.yaml`;
- moves the current `CHANGELOG.md` `Unreleased` notes into a dated version
  section;
- validates the generated files; and
- opens a release PR.

For local/manual release preparation, make the same edits:

1. Update `pyproject.toml`.
2. Update `plugin.yaml`.
3. Move the relevant `CHANGELOG.md` bullets from `Unreleased` into a dated
   version section such as `## [0.1.5] - 2026-07-08`.
4. Keep user-facing docs aligned if install, setup, provider behavior, or
   compatibility guidance changed.
5. For releases that touch Agent, Browser, Profiles, pricing, or Search/Fetch
   claims, confirm the README and release notes say this is an independent
   unaffiliated community plugin and that free-use assumptions are based on
   current TinyFish documentation.
6. Confirm credit-risking features still default to `deny`.

Run the full local suite:

```bash
python3 -m ruff format --check .
python3 -m ruff check .
python3 -m mypy hermes_plugin_tinyfish
python3 -m pytest
rm -rf dist && python3 -m build
```

Use a PR for protected `main`. Do not tag until the release PR has merged.

## Tag and Publish

After the generated release PR is merged, create an annotated tag matching the
package version:

```bash
git tag -a v0.1.5 -m "Release v0.1.5"
git push origin v0.1.5
```

The release workflow validates that the tag matches `pyproject.toml`, that
`plugin.yaml` has the same version, and that `CHANGELOG.md` contains a dated
section for that exact version. It uses only that version section as the GitHub
Release body, builds wheel and sdist artifacts, creates a GitHub Release, and
publishes to PyPI only when the repository variable enables PyPI publishing.

Release notes for capability releases should include:

- Search/Fetch are the safe default entry point.
- Agent, Browser, and Profile setup are credit-policy gated.
- The default policy is `deny`.
- Users can set `deny`, `request`, or `allow` with `hermes tinyfish credits`.

## Verify

Confirm GitHub Release assets include:

- `hermes_plugin_tinyfish-<version>-py3-none-any.whl`
- `hermes_plugin_tinyfish-<version>.tar.gz`

After the publish workflow completes, verify PyPI:

```bash
python3 -m pip index versions hermes-plugin-tinyfish --no-cache-dir
```

Then smoke-test a fresh virtualenv install.

## References

- [Hermes plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
- [Project releases](https://github.com/gabeosx/hermes-plugin-tinyfish/releases)
- [PyPI package](https://pypi.org/project/hermes-plugin-tinyfish/)
