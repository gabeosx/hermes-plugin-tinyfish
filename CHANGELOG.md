# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

## Unreleased

### Added

- Added current TinyFish Search filters (`include_domains`,
  `exclude_domains`, `pub_year_min`, and `pub_year_max`) and Fetch controls
  (`purpose`, CSS include/exclude selectors, conditional validators, and
  validator-return metadata) across both MCP and REST transports.
- Added compatibility with TinyFish CLI-seeded `MCP_TINYFISH_API_KEY`, while
  preserving `TINYFISH_API_KEY` precedence.
- Added a Hermes `after-install.md` guide that routes new installs through
  OAuth-first setup, diagnostics, and explicit paid-Browser policy.
- Added a minimal `hermes/` Git-install distribution so current Hermes security
  scanning evaluates runtime plugin files instead of repository development
  workflows and agent-maintenance tooling.

### Changed

- Forwarded operator Search/Fetch defaults consistently through MCP and REST,
  increased the REST Fetch timeout to TinyFish's documented 150-second batch
  recommendation, chunked direct calls at the 10-URL API cap, and restored
  output to input URL order.
- Expanded normalization to preserve news/research fields, selector recovery
  hints, conditional/cache metadata, authorship, links/images, and latency;
  JSON Fetch document trees now remain valid JSON.
- Bumped the tool-routing context to version 3 so it distinguishes transport-
  invariant operator defaults from one-off controls that require native MCP
  schemas.

### Fixed

- Closed billable Browser sessions when TinyFish returns an ID without a CDP
  URL, prevented cleanup exceptions from escaping the provider contract, and
  withheld Browser registration on Hermes hosts lacking approval hooks.
- Adopted Hermes's managed-secret credential writer with persisted-value
  verification while retaining the legacy writer on older supported hosts.

## [0.3.4] - 2026-08-13

### Fixed

- Replaced `hermes tinyfish usage` request-history output with the actual
  TinyFish wallet balance, auto-reload, pending top-up, and billing-rate API.
  Legacy-billing accounts now receive a clear explanation instead of request
  history, and the command states that no documented historical-spend API is
  available.

## [0.3.3] - 2026-08-12

### Fixed

- Replaced the unreadable raw dictionary output from `hermes tinyfish usage`
  with labeled Search and Fetch histories, pagination summaries, and clear
  partial-failure reporting while preserving `--json` for automation.

## [0.3.2] - 2026-08-11

### Added

- Added automated compatibility coverage for the Hermes 0.20.0 source release,
  alongside the packaged 0.18.2 and 0.19.0 compatibility jobs.
- Expanded `hermes tinyfish usage` to report both Search and Fetch operation
  history, including per-surface success or failure.

### Changed

- Bumped the ephemeral routing context to version 2 with research-paper and
  publication-year search modes, conditional Fetch validators, and explicit
  guidance not to silently drop requested controls when native MCP tools are
  unavailable.

### Fixed

- Made Browser session termination retry documented transient and transport
  failures within a bounded cleanup budget, honor capped `Retry-After` delays,
  and stop treating HTTP 404 as successful cleanup.

## [0.3.1] - 2026-08-04

### Fixed

- Added the required Hermes plugin enable step to the Python package install
  instructions before running TinyFish setup.

## [0.3.0] - 2026-08-04

### Added

- Added marked, once-per-active-context guidance so Hermes can infer when
  ordinary web requests should use generic provider tools and when
  TinyFish-specific controls require native MCP Search or Fetch without
  accumulating one new copy on every turn.
- Added nonblocking, source-aware update checks with a 24-hour profile-local
  cache, one-time conversational notices, install-appropriate update guidance,
  opt-outs, and non-networked diagnostics.

### Changed

- Expanded diagnostics to schema version 3 with routing state, installed and
  cached-latest versions, release channel, and update availability.
- Clarified that persistent Search/Fetch settings are REST fallback defaults,
  not required parity configuration for plain-language requests.

## [0.2.4] - 2026-07-22

### Fixed

- Made the merge-to-release path fully automatic by explicitly running checks
  for bot-created release PRs, merging them after validation, and dispatching
  the PyPI-trusted Release workflow for tagging, GitHub Release creation, and
  package publication.

## [0.2.3] - 2026-07-22

### Added

- Added conservative MCP OAuth failure classification, explicit reauthorization
  guidance, transport-specific live diagnostics, `/tinyfish-status`, and
  `hermes tinyfish reauth`.

### Changed

- Corrected the development build dependency floor to the latest available
  non-yanked release so clean CI environments can install the `dev` extra.
- Made MCP-to-REST degradation observable without logging raw OAuth responses,
  and clarified that a cached token file does not prove credential validity.
- Serialized plugin-triggered lazy MCP discovery within each process and
  limited live diagnostics to one discovery opportunity, reducing duplicate
  connection and OAuth refresh attempts without taking ownership of tokens.
- Stopped treating a zero exit status from Hermes's MCP login command as proof
  that browser reauthorization completed; MCP-only live diagnostics remain the
  authoritative verification step.
- Replaced nested Hermes subprocesses during interactive MCP login with a
  direct process handoff, preventing the plugin's parent process from competing
  for the OAuth callback port. Reauthorization now warns about shared Hermes
  homes and external gateway supervisors without attempting to manage them.
- Classified explicit OAuth failures nested inside task-group errors while
  preserving generic HTTP 400 as unknown, and added safe guidance for visually
  wrapped authorization URLs, single-flow callbacks, and unreliable login exit
  status.

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
