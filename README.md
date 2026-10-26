# HomeMate

One phone app for all the smart devices in the house. A small Python server
runs on the Mac mini and talks to each device; your phone opens it as an
app from the home screen.

| Brand | Status | How |
|---|---|---|
| Kasa plugs / strips / bulbs | ✅ | Local network, `python-kasa` |
| Wemo plugs / dimmers | ✅ | Local network, `pywemo` (works even though Belkin's cloud is gone) |
| Philips bulbs | ⏳ next | Hue bridge API, or WiZ local protocol |
| Ring cameras | ⏳ later | Unofficial cloud API |
| Resideo / First Alert alarms | ⏳ later | Read-only, via Google Home |
| Amazon Smart Plug | ❌ | No API; replace with a Kasa plug |

## How it's built

```
phone (web app) ──HTTP──▶ server.py ──▶ hub.py ──▶ adapters/kasa_adapter.py ──▶ Kasa plugs
                                                ├─▶ adapters/wemo_adapter.py ──▶ Wemo plugs
                                                └─▶ adapters/…               ──▶ …
```

- **`models.py`**: the brand-neutral `Device` and its `Capability` set
  (power, brightness). Everything above the adapters speaks only this.
- **`adapters/`**: one file per brand, each implementing `adapters/base.py`.
  A new brand means one new file and one line in `config.py`.
- **`hub.py`**: knows every device and routes commands to the adapter that
  owns it (by the `brand:` prefix in the id). If one brand fails to
  discover, the others still show up.
- **`server.py`**: the HTTP API (`/api/devices`, `/api/devices/{id}/power`, …)
  and the phone app files.
- **`web/`**: the phone app. Plain HTML/CSS/JS, no build step.

## Run it on the Mac mini

```bash
git clone https://github.com/djjr/HomeMate.git ~/HomeMate
cd ~/HomeMate
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env            # then put your Kasa login in .env

.venv/bin/uvicorn homemate.server:app --host 0.0.0.0 --port 8123
```

The first time, macOS may ask whether Terminal (or Python) can **find devices
on your local network**. Say **Allow**, or discovery finds nothing. You can
check later in System Settings → Privacy & Security → Local Network.

To try it with no devices at all: `HOMEMATE_ADAPTERS=demo .venv/bin/uvicorn homemate.server:app --port 8123`

To keep it running after reboots, see `deploy/com.homemate.server.plist`.

## Put it on your phone

1. On the home Wi-Fi, open `http://<mac-mini-name>.local:8123` in Safari.
   The Mac's name is in System Settings → General → Sharing → Local hostname.
2. Tap Share → **Add to Home Screen**. It now opens full-screen like an app.

**Away from home:** install [Tailscale](https://tailscale.com) (free) on the Mac
mini and your phone, and use the Mac's Tailscale address instead.
**Don't** open a port on your router: HomeMate has no login yet, so anyone
who found it could switch your devices.

## Tests

```bash
.venv/bin/pytest
```

They use the demo adapter, so they need no hardware.
