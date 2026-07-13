# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

## Unreleased

## [0.2.2] - 2026-07-13

### Added

- Added migration diagnostics for ignored `0.2.x` Agent, Profile setup, and
  model-tool credit-policy keys.
- Added authoritative Search/Fetch live diagnostics, a Browser-only paid live
  check, expanded compatibility CI, and structured issue forms.

### Changed

- Refocused the plugin on TinyFish Search and Fetch plus optional TinyFish
  Browser infrastructure controlled by Hermes.
- Simplified credit policy to Browser only, corrected usage reporting to use
  TinyFish Fetch operation history, and aligned runtime version reporting with
  installed package metadata.
- Promoted the package development classifier from Alpha to Beta for the
  feature-complete core-only scope.
- Extended supported and tested Python versions through Python 3.13.

### Removed

- Removed TinyFish Agent CLI commands, model-callable Agent tools, Browser
  Context Profile commands, and their Agent/Profile REST and policy surfaces.
  Existing remote TinyFish runs, profiles, credentials, and saved state are not
  modified.

## [0.2.1] - 2026-07-08

### Changed

- Made the tag-based release workflow idempotent for existing GitHub Releases
  and prevented duplicate/fallback tag runs from proceeding into PyPI publish.
- Added a manual PyPI release recovery path for cases where GitHub Release
  creation succeeds but the PyPI publish job is cancelled before upload.

## [0.2.0] - 2026-07-08

### Added

- Added default-deny TinyFish credit policies for Agent, Browser, Browser
  Context Profile setup, and model-callable TinyFish Agent tools.
- Added optional TinyFish Browser provider registration for Hermes browser
  automation.
- Added TinyFish Agent CLI commands, Browser Context Profile CLI commands,
  usage diagnostics, and `doctor --live-paid`.
- Added optional model-callable TinyFish Agent tools gated by credit policy.
- Added REST fallback support for TinyFish Search and Fetch options from
  `tinyfish.search` and `tinyfish.fetch` config.
- Added a manual Prepare Release workflow that computes the next version,
  promotes `Unreleased` changelog notes into a dated release section, updates
  package metadata, and opens a release PR.
- Added an Auto Release workflow so feature PR merges automatically create a
  release-prep PR and release-prep PR merges automatically create the release
  tag.
- Enabled auto-merge for generated release-prep PRs so the post-feature-merge
  release path can run without additional maintainer steps when repository
  auto-merge is enabled.
- Added shared release validation and release-note extraction used by both
  manual tag releases and automated post-merge releases.
- Added Python 3.10 compatibility guidance for coding agents and a CI
  `compileall` check across package code, scripts, and tests.

### Changed

- Updated README, reference docs, and operations docs to present this as an
  independent unaffiliated community plugin.
- Clarified that free Search/Fetch assumptions are based on current TinyFish
  documentation and may change.
- Expanded plugin metadata to advertise optional browser-provider support.
- Tightened release automation so GitHub Releases use only the matching
  changelog version section and PyPI publishing has one gated workflow path.

## [0.1.4] - 2026-07-07

### Changed

- Updated README badges and installation notes after PyPI publication.

## [0.1.3] - 2026-07-07

### Changed

- Enabled PyPI publication through Trusted Publishing.

## [0.1.2] - 2026-07-06

### Changed

- Corrected public package author metadata to use the repository owner handle.

## [0.1.1] - 2026-07-06

### Changed

- Clarified that Hermes Git plugin installs clone the repository default branch.
- Added gated PyPI publishing directly to the tag-based release workflow for future releases.

## [0.1.0] - 2026-07-06

### Added

- Initial TinyFish Hermes web provider.
- OAuth MCP-first routing for search and fetch.
- REST API-key fallback for `TINYFISH_API_KEY`.
- `hermes tinyfish setup`, `doctor`, and `status` CLI commands.
- CI, release, dependency review, and PyPI publishing workflows.
