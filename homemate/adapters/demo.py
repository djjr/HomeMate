"""Fake devices held in memory.

Lets you run the whole app (and the tests) without any hardware on the
network. Run with HOMEMATE_ADAPTERS=demo.
"""

from __future__ import annotations

from homemate.adapters.base import Adapter
from homemate.models import Capability, Device, DeviceNotFound


class DemoAdapter(Adapter):
    brand = "demo"

    def __init__(self) -> None:
        self._devices = {
            "lamp": Device(
                id=self.make_id("lamp"),
                name="Demo Living Room Lamp",
                brand=self.brand,
                kind="bulb",
                capabilities={Capability.POWER, Capability.BRIGHTNESS},
                is_on=True,
                brightness=70,
            ),
            "fan": Device(
                id=self.make_id("fan"),
                name="Demo Fan Plug",
                brand=self.brand,
                kind="plug",
                capabilities={Capability.POWER},
                is_on=False,
            ),
        }

    def _get(self, device_id: str) -> Device:
        try:
            return self._devices[self.native_id(device_id)]
        except KeyError:
            raise DeviceNotFound(device_id) from None

    async def discover(self) -> list[Device]:
        return list(self._devices.values())

    async def refresh(self, device_id: str) -> Device:
        return self._get(device_id)

    async def set_power(self, device_id: str, on: bool) -> Device:
        device = self._get(device_id)
        device.is_on = on
        return device

    async def set_brightness(self, device_id: str, level: int) -> Device:
        device = self._get(device_id)
        if Capability.BRIGHTNESS not in device.capabilities:
            return await super().set_brightness(device_id, level)
        device.brightness = level
        return device
