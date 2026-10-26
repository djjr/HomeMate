"""The brand-neutral device model.

Everything above the adapters (the hub, the API, the phone UI) speaks only
in these terms. A Kasa plug and a Wemo plug both become a `Device` with the
POWER capability; nothing outside their adapters knows they differ.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class Capability(str, Enum):
    """What a device can do. The UI decides which controls to draw from these."""

    POWER = "power"  # on/off
    BRIGHTNESS = "brightness"  # 1-100


@dataclass
class Device:
    # Globally unique and stable across restarts: "<brand>:<native id>".
    # The prefix also tells the hub which adapter owns the device.
    id: str
    name: str
    brand: str
    kind: str  # "plug", "bulb", "switch", ... (display hint only)
    capabilities: set[Capability] = field(default_factory=set)
    is_on: bool | None = None
    brightness: int | None = None
    online: bool = True

    def to_dict(self) -> dict:
        d = asdict(self)
        d["capabilities"] = sorted(c.value for c in self.capabilities)
        return d


class DeviceNotFound(KeyError):
    pass


class UnsupportedCapability(Exception):
    pass
