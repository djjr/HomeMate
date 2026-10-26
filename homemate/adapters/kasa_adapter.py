"""TP-Link Kasa plugs, power strips, switches and bulbs, via python-kasa.

Kasa devices answer on your home network directly, so this works without
the internet. Newer firmware encrypts that local traffic, which is why the
library wants your TP-Link (Kasa app) login: it derives the key from it.
"""

from __future__ import annotations

import logging

import kasa

from homemate.adapters.base import Adapter
from homemate.models import Capability, Device, DeviceNotFound

log = logging.getLogger(__name__)


class KasaAdapter(Adapter):
    brand = "kasa"

    def __init__(self, username: str | None = None, password: str | None = None) -> None:
        self._username = username
        self._password = password
        # native id -> the python-kasa object we talk to. For a power strip,
        # each outlet is its own entry pointing at the child object.
        self._handles: dict[str, kasa.Device] = {}

    async def discover(self) -> list[Device]:
        await self.close()  # drop connections from the previous scan
        found = await kasa.Discover.discover(
            username=self._username, password=self._password
        )
        devices: list[Device] = []
        for dev in found.values():
            try:
                await dev.update()
            except Exception:
                # One unplugged or misbehaving device shouldn't hide the rest.
                log.warning("Skipping Kasa device at %s", dev.host, exc_info=True)
                await dev.disconnect()
                continue
            # A power strip is one device on the network but several things
            # you want to switch. Flatten it: one HomeMate device per outlet.
            for handle in dev.children or [dev]:
                self._handles[handle.device_id] = handle
                devices.append(self._to_device(handle))
        return devices

    def _to_device(self, h: kasa.Device) -> Device:
        caps = {Capability.POWER}
        brightness = None
        # python-kasa describes what each device can do as named "features";
        # checking for one is more reliable than guessing from the model.
        if "brightness" in h.features:
            caps.add(Capability.BRIGHTNESS)
            brightness = h.features["brightness"].value
        return Device(
            id=self.make_id(h.device_id),
            name=h.alias or h.model,
            brand=self.brand,
            kind=h.device_type.value,
            capabilities=caps,
            is_on=h.is_on,
            brightness=brightness,
        )

    def _handle(self, device_id: str) -> kasa.Device:
        try:
            return self._handles[self.native_id(device_id)]
        except KeyError:
            raise DeviceNotFound(device_id) from None

    async def _update(self, h: kasa.Device) -> Device:
        # Children don't own a network connection; updating the parent strip
        # refreshes every outlet on it.
        await (h.parent or h).update()
        return self._to_device(h)

    async def refresh(self, device_id: str) -> Device:
        return await self._update(self._handle(device_id))

    async def set_power(self, device_id: str, on: bool) -> Device:
        h = self._handle(device_id)
        await (h.turn_on() if on else h.turn_off())
        return await self._update(h)

    async def set_brightness(self, device_id: str, level: int) -> Device:
        h = self._handle(device_id)
        if "brightness" not in h.features:
            return await super().set_brightness(device_id, level)
        await h.features["brightness"].set_value(level)
        return await self._update(h)

    async def close(self) -> None:
        for h in {h.parent or h for h in self._handles.values()}:
            await h.disconnect()
        self._handles.clear()
