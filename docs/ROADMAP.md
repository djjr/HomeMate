# HomeMate roadmap

The goal: one dashboard for on/off, schedules and vacation mode, with an
AI agent eventually keeping watch over the house.

## The guiding idea: an agent edits plans, the engine flips switches

It's tempting to give an agent a "turn on the porch light" button and let it
run the house minute by minute. That's fragile (if the agent or the
internet is down, nothing happens) and hard to trust (you can't see what it
will do tonight).

Instead, build it in layers, where each layer works without the ones above:

```
 ┌───────────────────────────────────────────┐
 │ 4. Agent         reads state, proposes/   │  optional, can be offline
 │                  edits schedules, alerts  │
 ├───────────────────────────────────────────┤
 │ 3. Dashboard     you, on your phone       │
 ├───────────────────────────────────────────┤
 │ 2. Rules engine  runs schedules & modes   │  always on, no AI, no internet
 │                  on the Mac mini          │
 ├───────────────────────────────────────────┤
 │ 1. Hub/adapters  talks to devices    ✅   │
 └───────────────────────────────────────────┘
```

Schedules are *data* (a list of rules saved to disk), not code. You edit that
data from the dashboard; later the agent edits the same data through the
same API. Everything the agent does is then visible, reversible and
running even if the agent isn't.

## Phase 1: Devices ✅

Kasa, Wemo, WiZ. Local control, phone web app.

## Phase 2: Schedules

- A rule = *when* + *which devices* + *what*. Examples:
  - every day at sunset → porch on; 23:00 → porch off
  - weekdays 06:30 → kitchen lamp on at 40%
- "When" supports fixed times and **sunrise/sunset** (computed locally from
  your location; no internet needed).
- Stored in a JSON file on the Mac mini (later SQLite, if it grows).
- The engine wakes up each minute, finds due rules and runs them. It
  re-checks after a restart so a reboot at 6:29 doesn't skip 6:30.
- Dashboard gets a Schedules tab: list, add, pause, delete.

## Phase 3: Rooms, groups and scenes

- Rooms ("Living room") and groups ("All outside lights").
- Scenes: one tap sets several devices ("Movie": lamp 20%, others off).
- Schedules can target a room or scene, not just one device.

## Phase 4: Vacation mode

- One switch: "Away from *date* to *date*".
- Pauses normal schedules and runs an **occupancy simulation**: selected
  lights go on in the evening and off at bedtime, with times shifted by a
  random ±20 minutes each day so it doesn't look automated.
- Optional: replay what you actually did in a normal week (needs Phase 5's
  history).
- Turns itself off when the dates end.

## Phase 5: History and alerts

- Log every state change and command (who did it: you, a schedule, the
  agent).
- Alerts to your phone when a device goes offline or something unusual
  happens.
- Bring in **Ring** (motion and doorbell events) and the **Resideo / First
  Alert** alarms (read-only, through Google Home) as *event sources*.

## Phase 6: The agent

- Expose HomeMate's API to an AI agent as tools via **MCP** (Model Context
  Protocol), the standard way to give an agent tools: `list_devices`,
  `set_power`, `list_schedules`, `propose_schedule`, `get_history`, ...
- What it could do: a morning briefing ("porch light was on all night;
  the Wemo in the garage has been offline since Tuesday"), suggestions
  ("you turn the lamp on at about 18:10 every day; want a schedule?"),
  vacation planning from a sentence ("I'm away the 3rd to the 10th").
- Guardrails, decided up front:
  - Can act directly: lights and plugs, schedules.
  - Must ask you first: anything that stays in effect for days (vacation
    mode), anything that touches the alarms or cameras.
  - Never: silencing, disabling or overriding smoke/CO alarms.
  - Every agent action appears in the history, tagged as the agent's.

## Before anything leaves the house: a login

Before HomeMate is reachable from outside your home network (or by an agent
running in the cloud), it needs authentication. Until then, use Tailscale
for remote access.
