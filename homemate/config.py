"""Settings come from environment variables (or a .env file next to the repo).

Keeping secrets like your TP-Link password out of the code means you can
commit everything safely; .env is listed in .gitignore.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from homemate.adapters.base import Adapter


def _load_dotenv(path: Path) -> None:
    # A ten-line .env reader so we don't need another dependency.
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


ROOT = Path(__file__).resolve().parent.parent
_load_dotenv(ROOT / ".env")


def build_adapters() -> list[Adapter]:
    names = os.environ.get("HOMEMATE_ADAPTERS", "kasa,wemo,wiz").split(",")
    adapters: list[Adapter] = []
    for name in (n.strip().lower() for n in names if n.strip()):
        # Imports live inside the branches so a missing library for a brand
        # you don't use can't stop the app from starting.
        if name == "demo":
            from homemate.adapters.demo import DemoAdapter

            adapters.append(DemoAdapter())
        elif name == "kasa":
            from homemate.adapters.kasa_adapter import KasaAdapter

            adapters.append(
                KasaAdapter(
                    username=os.environ.get("KASA_USERNAME"),
                    password=os.environ.get("KASA_PASSWORD"),
                )
            )
        elif name == "wemo":
            from homemate.adapters.wemo_adapter import WemoAdapter

            adapters.append(WemoAdapter())
        elif name == "wiz":
            from homemate.adapters.wiz_adapter import WizAdapter

            adapters.append(WizAdapter())
        else:
            raise ValueError(f"Unknown adapter in HOMEMATE_ADAPTERS: {name!r}")
    return adapters


def load_names() -> dict[str, str]:
    """Your own names for devices, keyed by HomeMate id: {"wiz:a8bb...": "Porch"}."""
    path = Path(os.environ.get("HOMEMATE_NAMES_FILE", ROOT / "names.json"))
    return json.loads(path.read_text()) if path.exists() else {}
