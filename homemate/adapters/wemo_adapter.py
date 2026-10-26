"""Belkin Wemo plugs, switches and dimmers, via pywemo.

Belkin shut down the Wemo cloud in January 2026, but the devices still
answer on your home network (a protocol called UPnP), which is all we use.

pywemo is a *synchronous* library: its calls block until the device replies.
Calling it directly would freeze our async server for every other user, so
each call is pushed onto a worker thread with asyncio.to_thread().
"""

from __future__ import annotations

import asyncio

import pywemo

from homemate.adapters.base import Adapter
from homemate.models import Capability, Device, DeviceNotFound


class WemoAdapter(Adapter):
    brand = "wemo"

    def __init__(self) -> None:
        self._handles: dict[str, pywemo.Switch] = {}

    async def discover(self) -> list[Device]:
        found = await asyncio.to_thread(pywemo.discover_devices)
        # Dimmers, Insight plugs and light switches are all subclasses of
        # Switch; motion sensors, crock pots etc. aren't, and we skip them.
        switches = [d for d in found if isinstance(d, pywemo.Switch)]
        self._handles = {d.serial_number: d for d in switches}
        return await asyncio.gather(*(asyncio.to_thread(self._read, d) for d in switches))

    def _read(self, d: pywemo.Switch) -> Device:
        # Runs on a worker thread: talks to the device synchronously.
        caps = {Capability.POWER}
        brightness = None
        if isinstance(d, pywemo.Dimmer):
            caps.add(Capability.BRIGHTNESS)
            brightness = d.get_brightness(force_update=True)
        return Device(
            id=self.make_id(d.serial_number),
            name=d.name,
            brand=self.brand,
            kind="dimmer" if isinstance(d, pywemo.Dimmer) else "plug",
            capabilities=caps,
            is_on=bool(d.get_state(force_update=True)),
            brightness=brightness,
        )

    def _handle(self, device_id: str) -> pywemo.Switch:
        try:
            return self._handles[self.native_id(device_id)]
        except KeyError:
            raise DeviceNotFound(device_id) from None

    async def refresh(self, device_id: str) -> Device:
        return await asyncio.to_thread(self._read, self._handle(device_id))

    async def set_power(self, device_id: str, on: bool) -> Device:
        d = self._handle(device_id)
        await asyncio.to_thread(d.on if on else d.off)
        return await asyncio.to_thread(self._read, d)

    async def set_brightness(self, device_id: str, level: int) -> Device:
        d = self._handle(device_id)
        if not isinstance(d, pywemo.Dimmer):
            return await super().set_brightness(device_id, level)
        await asyncio.to_thread(d.set_brightness, level)
        return await asyncio.to_thread(self._read, d)
