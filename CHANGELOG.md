# Changelog

All notable changes to this project are documented here. Versions follow
[Semantic Versioning](https://semver.org/).

## 0.3.0 - 2026-07-31

### Added

- Opt-in capture of the latest rejected camera frame in a protected,
  non-web-served directory, with single-file retention and restrictive
  permissions.
- Sanitized debug logs for snapshot attempts, image-quality measurements, and
  evaluation timing, plus diagnostic entity attributes.

### Changed

- Detect video-range near-black and dark low-contrast frames more reliably.
- Treat zero-confidence VLM responses as inconclusive and retain the previous
  valid sensor state.

## 0.2.1 - 2026-07-31

### Fixed

- Reject corrupt or overwhelmingly black camera frames locally and retry cold
  cameras up to three times before returning a sanitized error. Unusable frames
  are never sent to the configured VLM.

## 0.2.0 - 2026-07-31

### Added

- Editable image-evaluation prompt in initial setup and integration options,
  with automatic reload and non-configurable structured-output safeguards.

## 0.1.0 - 2026-07-31

### Added

- In-memory, single-snapshot occupancy evaluation with no video streaming.
- Local Ollama/OpenAI-compatible, OpenAI, and Google Gemini providers.
- Strict structured output for bed occupancy, wheelchair placement, combined
  confidence, and concise reasoning.
- Manual service evaluation, motion gating, overnight windows, sparse polling,
  and cooldown handling.
- Home Assistant config flow, occupancy binary sensor, service metadata, and
  translations.
- `secrets.yaml` and environment-variable credential indirection.
- Sanitized provider errors and bounded image/response handling.
- HACS metadata, brand icon, validation workflow, and focused unit tests.
