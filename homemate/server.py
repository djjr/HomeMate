"""HTTP API plus the phone web app, served from the Mac mini.

Run:  uvicorn homemate.server:app --host 0.0.0.0 --port 8123
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from homemate.config import build_adapters, load_names
from homemate.hub import Hub
from homemate.models import DeviceNotFound, UnsupportedCapability

logging.basicConfig(level=logging.INFO)

WEB_DIR = Path(__file__).parent / "web"


# Request bodies. Pydantic validates them before our code runs, so a bad
# level (say 0 or 500) is rejected with HTTP 422 automatically. They must be
# module-level: FastAPI resolves the type hints by name, and can't see
# classes defined inside a function.
class PowerRequest(BaseModel):
    on: bool


class BrightnessRequest(BaseModel):
    level: int = Field(ge=1, le=100)


def create_app(hub: Hub | None = None) -> FastAPI:
    # Taking the hub as a parameter lets tests pass one built on the demo
    # adapter instead of real hardware ("dependency injection").
    hub = hub or Hub(build_adapters(), load_names())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Discover in the background so the server answers immediately.
        task = asyncio.create_task(hub.discover())
        yield
        task.cancel()
        await hub.close()

    app = FastAPI(title="HomeMate", lifespan=lifespan)

    def run(call):
        # Translate the hub's domain errors into HTTP status codes in one place.
        async def wrapper():
            try:
                return (await call).to_dict()
            except DeviceNotFound:
                raise HTTPException(404, "Unknown device") from None
            except UnsupportedCapability as e:
                raise HTTPException(400, str(e)) from None
            except Exception as e:  # device unreachable, timeout, ...
                logging.exception("Device command failed")
                raise HTTPException(502, f"Device didn't respond: {e}") from None

        return wrapper()

    @app.get("/api/devices")
    async def list_devices():
        return {
            "devices": [d.to_dict() for d in hub.devices()],
            "errors": hub.adapter_errors,
        }

    @app.post("/api/discover")
    async def discover():
        await hub.discover()
        return await list_devices()

    @app.post("/api/devices/{device_id}/refresh")
    async def refresh(device_id: str):
        return await run(hub.refresh(device_id))

    @app.post("/api/devices/{device_id}/power")
    async def set_power(device_id: str, body: PowerRequest):
        return await run(hub.set_power(device_id, body.on))

    @app.post("/api/devices/{device_id}/brightness")
    async def set_brightness(device_id: str, body: BrightnessRequest):
        return await run(hub.set_brightness(device_id, body.level))

    # Mounted last so /api/* routes win; html=True serves index.html at "/".
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app


app = create_app()
