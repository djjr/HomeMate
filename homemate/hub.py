"""The hub: one place that knows every device and which adapter owns it.

The API layer calls the hub; the hub routes each call to the right adapter
using the brand prefix in the device id.
"""

from __future__ import annotations

import asyncio
import logging

from homemate.adapters.base import Adapter
from homemate.models import Device, DeviceNotFound

log = logging.getLogger(__name__)


class Hub:
    def __init__(self, adapters: list[Adapter], names: dict[str, str] | None = None) -> None:
        self._adapters = {a.brand: a for a in adapters}
        self._names = names or {}
        self._devices: dict[str, Device] = {}
        # Discovery can be slow; don't let two run at once.
        self._discover_lock = asyncio.Lock()
        self.adapter_errors: dict[str, str] = {}

    async def discover(self) -> list[Device]:
        async with self._discover_lock:
            # Ask every brand at the same time. return_exceptions=True means
            # one broken adapter (say, a bad Kasa password) is reported but
            # doesn't stop the other brands from showing up.
            results = await asyncio.gather(
                *(a.discover() for a in self._adapters.values()),
                return_exceptions=True,
            )
            devices: dict[str, Device] = {}
            self.adapter_errors = {}
            for brand, result in zip(self._adapters, results):
                if isinstance(result, BaseException):
                    log.warning("%s discovery failed: %r", brand, result)
                    self.adapter_errors[brand] = str(result) or type(result).__name__
                    continue
                for device in result:
                    devices[device.id] = device
            self._devices = {}
            for device in devices.values():
                self._store(device)
            return self.devices()

    def devices(self) -> list[Device]:
        return sorted(self._devices.values(), key=lambda d: d.name.lower())

    def _adapter_for(self, device_id: str) -> Adapter:
        if device_id not in self._devices:
            raise DeviceNotFound(device_id)
        return self._adapters[device_id.split(":", 1)[0]]

    async def refresh(self, device_id: str) -> Device:
        return self._store(await self._adapter_for(device_id).refresh(device_id))

    async def set_power(self, device_id: str, on: bool) -> Device:
        return self._store(await self._adapter_for(device_id).set_power(device_id, on))

    async def set_brightness(self, device_id: str, level: int) -> Device:
        level = max(1, min(100, level))
        adapter = self._adapter_for(device_id)
        return self._store(await adapter.set_brightness(device_id, level))

    def _store(self, device: Device) -> Device:
        # Your names win over whatever the device calls itself. Applied here,
        # in one place, so every adapter and every code path gets it.
        device.name = self._names.get(device.id, device.name)
        self._devices[device.id] = device
        return device

    async def close(self) -> None:
        await asyncio.gather(*(a.close() for a in self._adapters.values()))
