"""Snapshot evaluation and automatic gating for VLM Occupancy."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, time, timedelta
import logging
import os
from time import monotonic

from homeassistant.components.camera import async_get_image
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_API_KEYS,
    CONF_CAMERA_ENTITY_ID,
    CONF_CREDENTIAL_NAME,
    CONF_COOLDOWN,
    CONF_ENDPOINT,
    CONF_END_TIME,
    CONF_MODEL,
    CONF_MOTION_ENTITY_ID,
    CONF_POLL_INTERVAL,
    CONF_PROVIDER,
    CONF_START_TIME,
    DEFAULT_COOLDOWN,
    DEFAULT_END_TIME,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_START_TIME,
    DOMAIN,
    MAX_IMAGE_BYTES,
)
from .vlm_client import OccupancyResult, VLMClient, VLMClientError, create_client

_LOGGER = logging.getLogger(__name__)


class VLMOccupancyRuntime:
    """Own one config entry's client, gates, and last result."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: VLMClient
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.result: OccupancyResult | None = None
        self.last_evaluated: datetime | None = None
        self.last_error: str | None = None
        self._lock = asyncio.Lock()
        self._last_request_monotonic: float | None = None
        self._listeners: set[Callable[[], None]] = set()
        self._unsubscribers: list[Callable[[], None]] = []

    @classmethod
    def create(cls, hass: HomeAssistant, entry: ConfigEntry) -> "VLMOccupancyRuntime":
        """Create a runtime and resolve the credential from process memory."""
        credential_name = entry.data.get(CONF_CREDENTIAL_NAME, "")
        yaml_keys = hass.data.get(DOMAIN, {}).get(CONF_API_KEYS, {})
        api_key = (
            yaml_keys.get(credential_name) or os.environ.get(credential_name)
            if credential_name
            else None
        )
        client = create_client(
            entry.data[CONF_PROVIDER],
            async_get_clientsession(hass),
            entry.data[CONF_ENDPOINT],
            entry.data[CONF_MODEL],
            api_key,
        )
        return cls(hass, entry, client)

    def start(self) -> None:
        """Start only the configured sparse automatic triggers."""
        motion_entity_id = self.entry.data.get(CONF_MOTION_ENTITY_ID)
        if motion_entity_id:
            self._unsubscribers.append(
                async_track_state_change_event(
                    self.hass, [motion_entity_id], self._motion_changed
                )
            )
        poll_minutes = int(
            self.entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        )
        if poll_minutes > 0:
            self._unsubscribers.append(
                async_track_time_interval(
                    self.hass,
                    self._poll,
                    timedelta(minutes=poll_minutes),
                )
            )

    @callback
    def stop(self) -> None:
        """Stop all automatic triggers."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()

    @callback
    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe an entity to state changes."""
        self._listeners.add(listener)

        @callback
        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    async def async_evaluate(self, *, force: bool = False) -> OccupancyResult:
        """Fetch exactly one still image and evaluate it in memory."""
        async with self._lock:
            cooldown = int(self.entry.data.get(CONF_COOLDOWN, DEFAULT_COOLDOWN))
            now_monotonic = monotonic()
            if (
                not force
                and self.result is not None
                and self._last_request_monotonic is not None
                and now_monotonic - self._last_request_monotonic < cooldown
            ):
                return self.result

            self._last_request_monotonic = now_monotonic
            try:
                image = await async_get_image(
                    self.hass,
                    self.entry.data[CONF_CAMERA_ENTITY_ID],
                    timeout=15,
                )
                content = image.content
                content_type = image.content_type or "image/jpeg"
                if not content or len(content) > MAX_IMAGE_BYTES:
                    raise VLMClientError("Camera snapshot size is invalid")
                if not content_type.startswith("image/"):
                    raise VLMClientError("Camera did not return an image")
                self.result = await self.client.async_evaluate(content, content_type)
            except VLMClientError as err:
                self.last_error = str(err)
                self._notify_listeners()
                raise
            except Exception:
                self.last_error = "Camera snapshot unavailable"
                self._notify_listeners()
                raise VLMClientError("Camera snapshot unavailable") from None

            self.last_evaluated = dt_util.utcnow()
            self.last_error = None
            self._notify_listeners()
            return self.result

    @callback
    def _motion_changed(self, event: Event) -> None:
        new_state = event.data.get("new_state")
        if new_state is not None and new_state.state == STATE_ON and self._in_window():
            self.hass.async_create_task(
                self._async_background_evaluate("motion"),
                f"{self.entry.domain} motion evaluation",
            )

    async def _poll(self, now: datetime) -> None:
        if self._in_window(now):
            await self._async_background_evaluate("poll")

    async def _async_background_evaluate(self, trigger: str) -> None:
        try:
            await self.async_evaluate()
        except VLMClientError:
            # The runtime has already retained a sanitized message for the entity.
            _LOGGER.warning("VLM occupancy %s evaluation failed", trigger)

    def _in_window(self, now: datetime | None = None) -> bool:
        current = (now or dt_util.now()).time().replace(tzinfo=None)
        start = _parse_time(self.entry.data.get(CONF_START_TIME, DEFAULT_START_TIME))
        end = _parse_time(self.entry.data.get(CONF_END_TIME, DEFAULT_END_TIME))
        if start == end:
            return True
        if start < end:
            return start <= current < end
        return current >= start or current < end

    @callback
    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()


def _parse_time(value: str | time) -> time:
    """Normalize a TimeSelector value."""
    if isinstance(value, time):
        return value.replace(tzinfo=None)
    return time.fromisoformat(value)
