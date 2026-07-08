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

Normal releases are automated after PR merge:

1. Put user-facing release notes under `CHANGELOG.md` `Unreleased`.
2. Add one optional PR label before merging:
   - `release:patch`
   - `release:minor`
   - `release:major`
   - `release:none`
3. Merge the feature PR.

After merge, the **Auto Release** workflow opens a release-prep PR when
`Unreleased` has content and enables GitHub auto-merge for that PR. It defaults
to `release:patch` if no release label is present. Repository auto-merge must
be enabled for this to complete without human intervention.

After the generated release-prep PR auto-merges, **Auto Release** validates
release metadata, builds artifacts, creates and pushes the matching `vX.Y.Z`
tag, creates the GitHub Release, and publishes to PyPI when
`PYPI_PUBLISH_ENABLED == true`.

Use the **Prepare Release Manually** workflow only when a release PR needs to be
created outside the normal feature-PR flow. Choose a `patch`, `minor`, or
`major` bump, or pass an explicit version such as `0.2.0`.

The prepare-release workflow:

- computes the next version when only a bump is supplied;
- updates `pyproject.toml`;
- updates `plugin.yaml`;
- moves the current `CHANGELOG.md` `Unreleased` notes into a dated version
  section;
- validates the generated files; and
- opens a release PR and enables auto-merge. Merging that release PR triggers
  automatic tag creation.

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

Use a PR for protected `main`. Do not create tags or GitHub Releases by hand in
the normal flow.

## Tag and Publish

Manual tagging is only needed if automation is disabled or a release must be
recovered by hand. In that case, build the artifacts, create the GitHub Release,
and create an annotated tag matching the package version:

```bash
git tag -a v0.1.5 -m "Release v0.1.5"
git push origin v0.1.5
```

The tag-based release workflow remains available for manually pushed tags. It
validates that the tag matches `pyproject.toml`, that
`plugin.yaml` has the same version, and that `CHANGELOG.md` contains a dated
section for that exact version. It uses only that version section as the GitHub
Release body, builds wheel and sdist artifacts, creates a GitHub Release, and
publishes to PyPI only when the repository variable enables PyPI publishing.

If the GitHub Release succeeds but PyPI publishing is cancelled before the
package upload, rerun the **Release** workflow manually with the existing tag.
The manual dispatch checks out that tag, refreshes the GitHub Release assets,
refuses to publish if that version is already present on PyPI, and then runs
the PyPI Trusted Publishing step. Do not delete and recreate release tags for
this recovery case.

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
