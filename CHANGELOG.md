# Changelog

All notable changes to this project are documented here. Versions follow
[Semantic Versioning](https://semver.org/).

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
