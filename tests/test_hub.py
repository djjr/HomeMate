import pytest

from homemate.adapters.base import Adapter
from homemate.adapters.demo import DemoAdapter
from homemate.hub import Hub
from homemate.models import DeviceNotFound, UnsupportedCapability


class BrokenAdapter(Adapter):
    """Stands in for a brand whose discovery blows up (bad password, etc.)."""

    brand = "broken"

    async def discover(self):
        raise RuntimeError("login failed")

    async def refresh(self, device_id):
        raise AssertionError

    async def set_power(self, device_id, on):
        raise AssertionError


async def test_one_broken_brand_does_not_hide_the_others():
    hub = Hub([BrokenAdapter(), DemoAdapter()])
    devices = await hub.discover()
    assert {d.id for d in devices} == {"demo:lamp", "demo:fan"}
    assert hub.adapter_errors == {"broken": "login failed"}


async def test_commands_route_to_the_owning_adapter():
    hub = Hub([DemoAdapter()])
    await hub.discover()
    assert (await hub.set_power("demo:fan", True)).is_on is True
    assert (await hub.set_brightness("demo:lamp", 30)).brightness == 30


async def test_brightness_is_clamped_to_valid_range():
    hub = Hub([DemoAdapter()])
    await hub.discover()
    assert (await hub.set_brightness("demo:lamp", 500)).brightness == 100


async def test_unknown_device_and_unsupported_capability():
    hub = Hub([DemoAdapter()])
    await hub.discover()
    with pytest.raises(DeviceNotFound):
        await hub.set_power("demo:nope", True)
    with pytest.raises(UnsupportedCapability):
        await hub.set_brightness("demo:fan", 50)


async def test_your_names_override_device_names():
    hub = Hub([DemoAdapter()], names={"demo:fan": "Bedroom Fan"})
    await hub.discover()
    assert {d.name for d in hub.devices()} == {"Bedroom Fan", "Demo Living Room Lamp"}
    # ...and still apply after a command returns fresh state from the adapter.
    assert (await hub.set_power("demo:fan", True)).name == "Bedroom Fan"
