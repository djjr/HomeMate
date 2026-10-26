"""Philips Smart Wi-Fi (WiZ) bulbs, via pywizlight.

WiZ bulbs take simple JSON messages over UDP on your home network, so no
hub and no cloud are needed. One catch: the names you typed into the WiZ
app live in WiZ's cloud, not on the bulb. Locally a bulb only knows its MAC
address, so name them in names.json (see README).
"""

from __future__ import annotations

import asyncio

from pywizlight import PilotBuilder, discovery, wizlight

from homemate.adapters.base import Adapter
from homemate.models import Capability, Device, DeviceNotFound


def _to_wiz(level: int) -> int:
    # HomeMate uses 1-100 everywhere; pywizlight wants 0-255.
    return round(level * 255 / 100)


def _from_wiz(value: int | None) -> int | None:
    return None if value is None else max(1, round(value * 100 / 255))


class WizAdapter(Adapter):
    brand = "wiz"

    def __init__(self) -> None:
        self._handles: dict[str, wizlight] = {}

    async def discover(self) -> list[Device]:
        await self.close()
        bulbs = await discovery.discover_lights()
        self._handles = {b.mac: b for b in bulbs}
        return await asyncio.gather(*(self._read(b) for b in bulbs))

    async def _read(self, bulb: wizlight) -> Device:
        state = await bulb.updateState()
        return Device(
            id=self.make_id(bulb.mac),
            name=f"WiZ bulb {bulb.mac[-4:]}",
            brand=self.brand,
            kind="bulb",
            capabilities={Capability.POWER, Capability.BRIGHTNESS},
            is_on=state.get_state() if state else None,
            brightness=_from_wiz(state.get_brightness()) if state else None,
            online=state is not None,
        )

    def _handle(self, device_id: str) -> wizlight:
        try:
            return self._handles[self.native_id(device_id)]
        except KeyError:
            raise DeviceNotFound(device_id) from None

    async def refresh(self, device_id: str) -> Device:
        return await self._read(self._handle(device_id))

    async def set_power(self, device_id: str, on: bool) -> Device:
        bulb = self._handle(device_id)
        await (bulb.turn_on() if on else bulb.turn_off())
        return await self._read(bulb)

    async def set_brightness(self, device_id: str, level: int) -> Device:
        bulb = self._handle(device_id)
        # Setting brightness on a WiZ bulb also turns it on, which is what
        # you'd expect from dragging a slider.
        await bulb.turn_on(PilotBuilder(brightness=_to_wiz(level)))
        return await self._read(bulb)

    async def close(self) -> None:
        await asyncio.gather(*(b.async_close() for b in self._handles.values()))
        self._handles.clear()
