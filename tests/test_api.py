from fastapi.testclient import TestClient

from homemate.adapters.demo import DemoAdapter
from homemate.hub import Hub
from homemate.server import create_app


def client() -> TestClient:
    return TestClient(create_app(Hub([DemoAdapter()])))


def test_lists_devices_after_startup_discovery():
    with client() as c:  # "with" runs the app's startup, which discovers
        c.post("/api/discover")
        names = [d["name"] for d in c.get("/api/devices").json()["devices"]]
    assert names == ["Demo Fan Plug", "Demo Living Room Lamp"]


def test_power_and_brightness_commands():
    with client() as c:
        c.post("/api/discover")
        assert c.post("/api/devices/demo:fan/power", json={"on": True}).json()["is_on"]
        r = c.post("/api/devices/demo:lamp/brightness", json={"level": 25})
        assert r.json()["brightness"] == 25


def test_errors_map_to_http_status_codes():
    with client() as c:
        c.post("/api/discover")
        assert c.post("/api/devices/demo:nope/power", json={"on": True}).status_code == 404
        assert c.post("/api/devices/demo:fan/brightness", json={"level": 50}).status_code == 400
        assert c.post("/api/devices/demo:lamp/brightness", json={"level": 0}).status_code == 422


def test_serves_the_phone_app():
    with client() as c:
        assert "HomeMate" in c.get("/").text
