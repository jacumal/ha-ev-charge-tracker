import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const source = readFileSync(
  new URL("../custom_components/ev_charge_tracker/frontend/ev-charge-tracker-card.js", import.meta.url),
  "utf8",
);

function createCard(config, states = {}) {
  const registry = new Map();
  class HTMLElement {
    attachShadow() {
      this.shadowRoot = { innerHTML: "" };
      return this.shadowRoot;
    }
  }
  runInNewContext(source, {
    HTMLElement,
    customElements: { define: (name, constructor) => registry.set(name, constructor) },
    window: {},
  });
  const Card = registry.get("ev-charge-tracker-card");
  const card = new Card();
  card.setConfig(config);
  card.hass = { states, locale: { language: "es-ES" } };
  return card.shadowRoot.innerHTML;
}

test("does not present an unconfigured status sensor as idle", () => {
  const html = createCard({ entities: {} });
  assert.match(html, /Estado sin configurar/);
  assert.doesNotMatch(html, />En espera</);
});

test("distinguishes unavailable status from a real idle state", () => {
  const unavailable = createCard(
    { entities: { status: "sensor.charge_status" } },
    { "sensor.charge_status": { state: "unavailable", attributes: {} } },
  );
  const idle = createCard(
    { entities: { status: "sensor.charge_status" } },
    { "sensor.charge_status": { state: "idle", attributes: {} } },
  );
  assert.match(unavailable, /Estado no disponible/);
  assert.match(idle, />En espera</);
});

test("labels a calculated fixed-price cost as applied, not measured", () => {
  const html = createCard(
    { entities: { status: "sensor.status", cost: "sensor.cost" } },
    {
      "sensor.status": { state: "idle", attributes: {} },
      "sensor.cost": {
        state: "3.25",
        attributes: { cost_status: "complete", known_cost: 3.25, tariff_estimated: false },
      },
    },
  );
  assert.match(html, /Precio aplicado/);
  assert.doesNotMatch(html, />Medido</);
});

test("shows estimated tariff allocation and missing tariff data distinctly", () => {
  const estimated = createCard(
    { entities: { cost: "sensor.cost" } },
    { "sensor.cost": { state: "2.5", attributes: { tariff_estimated: true } } },
  );
  const missing = createCard({ entities: {} });
  assert.match(estimated, /Estimado/);
  assert.match(missing, /Sin datos/);
});

test("clamps the history display to at most 50 records", () => {
  const sessions = Array.from({ length: 60 }, (_, index) => ({
    started_at: `2026-01-${String((index % 28) + 1).padStart(2, "0")}T10:00:00Z`,
    energy_kwh: 10,
    cost: 2,
    cost_status: "complete",
  }));
  const html = createCard(
    { max_history: 1000, entities: { history: "sensor.history" } },
    { "sensor.history": { state: "60", attributes: { sessions } } },
  );
  assert.match(html, /50 registros/);
});
