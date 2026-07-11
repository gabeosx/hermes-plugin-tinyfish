# Release Operations

Use this runbook when preparing a public Hermes TinyFish plugin release.

GitHub Releases are the primary Hermes-native channel. PyPI is secondary for
environments that load `hermes_agent.plugins` entry points. Do not create a
tag, GitHub Release, or PyPI publication without explicit authorization.

## Release Automation

Normal releases follow the pull-request label on the merged change:

- `release:none` merges work without preparing a release.
- `release:patch`, `release:minor`, or `release:major` select the bump.
- A non-empty `CHANGELOG.md` `Unreleased` section defaults to patch when no
  release label is present.

After a release-triggering merge, **Auto Release** opens a release-prep PR. The
prep workflow updates `pyproject.toml`, `plugin.yaml`, and `CHANGELOG.md`, then
enables auto-merge when repository settings allow it. Merging that PR creates
the matching tag and GitHub Release; PyPI publication runs only when
`PYPI_PUBLISH_ENABLED == true`.

Use **Prepare Release Manually** only when a release-prep PR is needed outside
the normal feature-PR flow. The tag-based **Release** workflow remains available
for authorized recovery and validates metadata before publishing.

## Core-Only `0.3.0` Gates

The core-only implementation must merge with `release:none`. Set the package
classifier to Beta for the feature-complete core-only scope, but do not bump
package or manifest versions in that PR.

Against merged `main`, complete and record the compatibility runbook using
disposable Hermes homes:

1. Fresh Git install and update from released `0.2.1`.
2. Retired-policy reporting without implicit config mutation, followed by an
   explicit reset that leaves only `browser: deny`.
3. No registered TinyFish Agent tools and no accepted `agent`/`profiles` CLI
   commands.
4. MCP-only and REST-only live Search/Fetch checks, with TinyFish selected for
   both Hermes web providers and no provider fallback.
5. One explicitly approved Browser create/close check.
6. Gateway restart with a healthy replacement process and sanitized logs free
   of import, registration, and stale-tool errors.

Only after every gate passes should a release-readiness PR:

- confirm the Beta classifier still matches the release scope;
- ensure Python 3.13 metadata is present;
- include the sanitized compatibility report; and
- merge with `release:minor` to prepare `0.3.0`.

After automation creates the release, verify GitHub/PyPI metadata and smoke-test
fresh installs from both distribution paths.

## General Preflight

Check the working tree and version metadata:

```bash
git status --short
```

`pyproject.toml` and `plugin.yaml` must match. A public release must also have a
dated `CHANGELOG.md` section for that exact version. Preserve historical notes,
including the removed `0.2.x` Agent/Profile behavior.

Documentation is part of feature completion. Update README, reference docs,
operations docs, and migration guidance whenever setup, commands, providers,
policy, compatibility, or release behavior changes.

Run the full local suite:

```bash
python3 -m ruff format --check .
python3 -m ruff check .
python3 -m compileall hermes_plugin_tinyfish scripts tests
python3 -m mypy hermes_plugin_tinyfish
python3 -m pytest --cov=hermes_plugin_tinyfish --cov-report=term-missing --cov-fail-under=70
rm -rf dist && python3 -m build
```

Use a PR for protected `main`; do not create release tags by hand in the normal
flow.

## Manual Recovery

Manual tagging is only for explicitly authorized recovery when automation is
disabled:

```bash
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin v0.3.0
```

The tag-based workflow validates the tag against `pyproject.toml`, verifies the
same version in `plugin.yaml`, extracts only the matching dated changelog
section, builds wheel/sdist artifacts, creates or refreshes the GitHub Release,
and publishes to PyPI only when enabled.

If GitHub Release creation succeeds but PyPI upload is cancelled, rerun the
**Release** workflow manually with the existing tag. The workflow refuses a
duplicate PyPI version. Do not delete and recreate the release tag.

## Post-Release Verification

Confirm GitHub Release assets include:

- `hermes_plugin_tinyfish-<version>-py3-none-any.whl`
- `hermes_plugin_tinyfish-<version>.tar.gz`

Then verify PyPI and perform the Git and PyPI user-install smoke tests:

```bash
python3 -m pip index versions hermes-plugin-tinyfish --no-cache-dir
```

Record artifact hashes, install results, reported runtime version, provider
selection, and any skipped live checks without recording secrets.

## References

- [Compatibility testing](compatibility-testing.md)
- [User install smoke test](user-install-smoke-test.md)
- [Project releases](https://github.com/gabeosx/hermes-plugin-tinyfish/releases)
- [PyPI package](https://pypi.org/project/hermes-plugin-tinyfish/)
