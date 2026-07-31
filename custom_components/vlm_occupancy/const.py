"""Constants for the VLM Occupancy integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "vlm_occupancy"
PLATFORMS: Final = ["binary_sensor"]

CONF_CAMERA_ENTITY_ID: Final = "camera_entity_id"
CONF_PROVIDER: Final = "provider"
CONF_ENDPOINT: Final = "endpoint"
CONF_MODEL: Final = "model"
CONF_CREDENTIAL_NAME: Final = "credential_name"
CONF_API_KEYS: Final = "api_keys"
CONF_MOTION_ENTITY_ID: Final = "motion_entity_id"
CONF_START_TIME: Final = "start_time"
CONF_END_TIME: Final = "end_time"
CONF_POLL_INTERVAL: Final = "poll_interval_minutes"
CONF_COOLDOWN: Final = "cooldown_seconds"

PROVIDER_OLLAMA: Final = "ollama"
PROVIDER_OPENAI: Final = "openai"
PROVIDER_GEMINI: Final = "gemini"
PROVIDERS: Final = (PROVIDER_OLLAMA, PROVIDER_OPENAI, PROVIDER_GEMINI)

DEFAULT_ENDPOINTS: Final = {
    PROVIDER_OLLAMA: "http://localhost:11434/v1",
    PROVIDER_OPENAI: "https://api.openai.com/v1",
    PROVIDER_GEMINI: "https://generativelanguage.googleapis.com/v1beta",
}
DEFAULT_MODELS: Final = {
    PROVIDER_OLLAMA: "llava",
    PROVIDER_OPENAI: "gpt-4.1-mini",
    PROVIDER_GEMINI: "gemini-2.5-flash",
}
DEFAULT_CREDENTIAL_NAMES: Final = {
    PROVIDER_OLLAMA: "",
    PROVIDER_OPENAI: "OPENAI_API_KEY",
    PROVIDER_GEMINI: "GEMINI_API_KEY",
}

DEFAULT_START_TIME: Final = "00:00:00"
DEFAULT_END_TIME: Final = "00:00:00"
DEFAULT_POLL_INTERVAL: Final = 0
DEFAULT_COOLDOWN: Final = 30

SERVICE_EVALUATE: Final = "evaluate"
ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_FORCE: Final = "force"

MAX_IMAGE_BYTES: Final = 20 * 1024 * 1024
