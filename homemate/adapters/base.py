"""The contract every brand adapter fulfils.

Adding a new brand means writing one subclass of `Adapter`; the hub, API and
UI need no changes. That is the whole point of the adapter pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from homemate.models import Device, UnsupportedCapability


class Adapter(ABC):
    brand: str  # used as the device id prefix, e.g. "kasa"

    @abstractmethod
    async def discover(self) -> list[Device]:
        """Find devices and return their current state."""

    @abstractmethod
    async def refresh(self, device_id: str) -> Device:
        """Re-read one device's state from the hardware."""

    @abstractmethod
    async def set_power(self, device_id: str, on: bool) -> Device:
        """Turn a device on or off and return its new state."""

    async def set_brightness(self, device_id: str, level: int) -> Device:
        # Not abstract: most plugs can't dim, so the default is a clear refusal.
        raise UnsupportedCapability(f"{device_id} does not support brightness")

    async def close(self) -> None:
        """Release network connections. Override if the library needs it."""

    # Helpers so subclasses build ids consistently.
    def make_id(self, native_id: str) -> str:
        return f"{self.brand}:{native_id}"

    def native_id(self, device_id: str) -> str:
        return device_id.split(":", 1)[1]
