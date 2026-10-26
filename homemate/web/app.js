// The phone UI. It only knows the brand-neutral API, never Kasa or Wemo.

const list = document.getElementById("devices");
const statusEl = document.getElementById("status");
const template = document.getElementById("device-card");

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.classList.toggle("error", isError);
}

async function api(path, body) {
  const res = await fetch(`/api/${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

// Draw (or redraw) one device's card from its state.
function renderCard(device, card = template.content.firstElementChild.cloneNode(true)) {
  card.dataset.id = device.id;
  card.classList.toggle("offline", !device.online);
  card.querySelector(".name").textContent = device.name;
  card.querySelector(".meta").textContent = `${device.brand} ${device.kind}`;

  const power = card.querySelector(".power");
  power.checked = !!device.is_on;
  power.disabled = !device.capabilities.includes("power");

  const slider = card.querySelector(".brightness");
  slider.hidden = !device.capabilities.includes("brightness");
  if (device.brightness != null) slider.value = device.brightness;
  return card;
}

// Last state the server reported for each device, keyed by id.
const devicesById = new Map();

// Send a command, and show the state the server reports back. If it
// fails, redraw from the old state so the toggle doesn't lie to you.
async function command(card, path, body) {
  const previous = devicesById.get(card.dataset.id);
  try {
    const device = await api(`devices/${encodeURIComponent(card.dataset.id)}/${path}`, body);
    devicesById.set(device.id, device);
    renderCard(device, card);
    setStatus("");
  } catch (err) {
    renderCard(previous, card);
    setStatus(err.message, true);
  }
}

// One listener on the list handles every card ("event delegation"),
// so cards added later work without wiring each one up.
list.addEventListener("change", (event) => {
  const card = event.target.closest(".card");
  if (!card) return;
  if (event.target.matches(".power")) {
    command(card, "power", { on: event.target.checked });
  } else if (event.target.matches(".brightness")) {
    command(card, "brightness", { level: Number(event.target.value) });
  }
});

function renderAll({ devices, errors }) {
  devicesById.clear();
  list.replaceChildren(
    ...devices.map((d) => {
      devicesById.set(d.id, d);
      return renderCard(d);
    }),
  );
  const problems = Object.entries(errors).map(([brand, msg]) => `${brand}: ${msg}`);
  if (problems.length) setStatus(problems.join(" · "), true);
  else setStatus(devices.length ? "" : "No devices found yet. Tap Scan.");
}

async function load() {
  try {
    renderAll(await api("devices"));
  } catch (err) {
    setStatus(`Can't reach HomeMate: ${err.message}`, true);
  }
}

document.getElementById("discover").addEventListener("click", async () => {
  setStatus("Scanning your network…");
  try {
    renderAll(await api("discover", {}));
  } catch (err) {
    setStatus(err.message, true);
  }
});

// Refresh when you come back to the app, since someone may have used a wall switch.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") load();
});

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");
load();
