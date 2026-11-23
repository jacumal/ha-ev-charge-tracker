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
  assert.match(idle, /En espera/);
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
    { max_history: 1000, display_mode: "complete", entities: { history: "sensor.history" } },
    { "sensor.history": { state: "60", attributes: { sessions } } },
  );
  assert.match(html, /50 registros/);
});

test("renders energy and cost history charts from stored sessions", () => {
  const html = createCard(
    { entities: { history: "sensor.history" } },
    { "sensor.history": { state: "2", attributes: { sessions: [
      { started_at: "2026-11-20T10:00:00Z", energy_kwh: 12, cost: 2.4, cost_status: "complete" },
      { started_at: "2026-11-21T10:00:00Z", energy_kwh: 18, known_cost: 1.8, cost: null, cost_status: "partial" },
    ] } } },
  );
  assert.match(html, /Energía por carga/);
  assert.match(html, /Coste por carga/);
  assert.match(html, /parcial/);
  assert.match(html, /18/);
});

test("does not plot null energy or unknown cost as zero", () => {
  const html = createCard(
    { entities: { history: "sensor.history" } },
    { "sensor.history": { state: "1", attributes: { sessions: [
      { started_at: "2026-11-21T10:00:00Z", energy_kwh: null, cost: null, known_cost: null },
    ] } } },
  );
  assert.match(html, /Aún no hay datos de energía suficientes/);
  assert.match(html, /Sin costes calculables todavía/);
});

test("keeps chart placeholders when history is empty", () => {
  const html = createCard(
    { entities: { history: "sensor.history" } },
    { "sensor.history": { state: "0", attributes: { sessions: [] } } },
  );
  assert.match(html, /Aún no hay datos de energía suficientes/);
  assert.match(html, /Sin costes calculables todavía/);
});

test("keeps known cost visible when the session energy reading is missing", () => {
  const html = createCard(
    { entities: { history: "sensor.history" } },
    { "sensor.history": { state: "1", attributes: { sessions: [
      { started_at: "2026-11-21T10:00:00Z", energy_kwh: null, cost: null, known_cost: 1.25, cost_status: "partial" },
    ] } } },
  );
  assert.match(html, /Coste por carga/);
  assert.match(html, /1,25/);
  assert.doesNotMatch(html, /Sin costes calculables todavía/);
});

test("shows live battery SOC and odometer from the selected profile entities", () => {
  const html = createCard(
    { entities: { current_soc: "sensor.leapmotor_precise_battery", odometer: "sensor.leapmotor_odometer" } },
    {
      "sensor.leapmotor_precise_battery": { state: "87.4", attributes: { unit_of_measurement: "%" } },
      "sensor.leapmotor_odometer": { state: "12345", attributes: { unit_of_measurement: "km" } },
    },
  );
  assert.match(html, /BATERÍA ACTUAL/);
  assert.match(html, /87,4%/);
  assert.match(html, /Odómetro/);
  assert.match(html, /12\.345 km/);
  assert.match(html, /vehicle-telemetry/);
  assert.match(html, /Datos complementarios del vehículo/);
});

test("renders a transparent vehicle silhouette and cable state without a custom image", () => {
  const html = createCard(
    { name: "Leapmotor C10", vehicle_visual: { visual_brand: "Leapmotor", visual_model: "C10", visual_color: "#AABBCC", visual_body_style: "suv" }, entities: { status: "sensor.status" } },
    { "sensor.status": { state: "idle", attributes: {} } },
  );
  assert.match(html, /vehicle-visual/);
  assert.match(html, /Leapmotor C10/);
  assert.match(html, /vehicle-body/);
  assert.match(html, /state-unknown/);
  assert.match(html, /Conexión sin monitorizar/);
});

test("animates energy flow only while charging and supports local transparent images", () => {
  const html = createCard(
    { vehicle_visual: { visual_brand: "Leapmotor", visual_model: "C10", visual_image: "/local/ev-charge-tracker/c10.webp" }, entities: { status: "sensor.status" } },
    { "sensor.status": { state: "charging", attributes: {} } },
  );
  assert.ok(html.includes("c10.webp"));
  assert.match(html, /state-charging/);
  assert.match(html, /energy-flow/);
});

test("distinguishes connected idle and error vehicle states", () => {
  const connected = createCard(
    { vehicle_visual: {}, entities: { status: "sensor.status", plugged: "binary_sensor.plugged" } },
    { "sensor.status": { state: "idle", attributes: {} }, "binary_sensor.plugged": { state: "on", attributes: {} } },
  );
  const error = createCard(
    { entities: { status: "sensor.status" } },
    { "sensor.status": { state: "needs_attention", attributes: {} } },
  );
  assert.match(connected, /state-connected/);
  assert.match(connected, /Cable conectado/);
  assert.match(error, /state-error/);
  assert.match(error, /requiere atención/);
});


test("keeps the vehicle in completed state after the live charging sensor returns to idle", () => {
  const html = createCard(
    { entities: { status: "sensor.status", history: "sensor.history" } },
    {
      "sensor.status": { state: "idle", attributes: {} },
      "sensor.history": { state: "1", attributes: {
        current_session: null,
        latest_session: { status: "completed", completed_at: "2026-11-23T07:00:00Z" },
        sessions: [],
      } },
    },
  );
  assert.match(html, /state-completed/);
  assert.match(html, /Carga finalizada/);
});


test("does not interpret an unavailable cable sensor as physically disconnected", () => {
  const html = createCard(
    { entities: { status: "sensor.status", plugged: "binary_sensor.plugged" } },
    {
      "sensor.status": { state: "idle", attributes: {} },
      "binary_sensor.plugged": { state: "unavailable", attributes: {} },
    },
  );
  assert.match(html, /state-unknown/);
  assert.match(html, /Conexión no disponible/);
  assert.doesNotMatch(html, /Cable desconectado/);
});


test("positions cable and connector using the vehicle-specific port anchor", () => {
  const html = createCard(
    { vehicle_visual: { visual_port_x: 55, visual_port_y: 30 }, entities: { status: "sensor.status" } },
    { "sensor.status": { state: "charging", attributes: {} } },
  );
  assert.match(html, /cx="143" cy="33"/);
  assert.match(html, /M143 33 C/);
});


test("flags contradictory charging and unplugged signals as an attention state", () => {
  const html = createCard(
    { entities: { status: "sensor.status", plugged: "binary_sensor.plugged" } },
    {
      "sensor.status": { state: "charging", attributes: {} },
      "binary_sensor.plugged": { state: "off", attributes: {} },
    },
  );
  assert.match(html, /state-error/);
  assert.match(html, /Carga activa con cable desconectado/);
  assert.match(html, /class="vehicle-stage state-error"/);
  assert.doesNotMatch(html, /class="vehicle-stage state-charging"/);
});



test("supports compact, balanced and complete information density in Lovelace config", () => {
  const compact = createCard({ display_mode: "compact", entities: { status: "sensor.status" } }, { "sensor.status": { state: "idle", attributes: {} } });
  const complete = createCard({ display_mode: "complete", entities: { status: "sensor.status" } }, { "sensor.status": { state: "idle", attributes: {} } });
  assert.match(compact, /mode-compact/);
  assert.doesNotMatch(compact, /Energía por carga/);
  assert.match(complete, /Energía por carga/);
  assert.match(complete, /Histórico de cargas/);
});


test("supports automatic, light and dark card appearance independently of information density", () => {
  const automatic = createCard({ theme_mode: "auto", display_mode: "compact", entities: {} });
  const light = createCard({ theme_mode: "light", display_mode: "balanced", entities: {} });
  const dark = createCard({ theme_mode: "dark", display_mode: "complete", entities: {} });
  assert.match(automatic, /data-theme="auto"/);
  assert.match(light, /data-theme="light"/);
  assert.match(dark, /data-theme="dark"/);
  assert.match(dark, /--primary-text-color:#f5f5f7/);
  assert.match(light, /--primary-text-color:#1d1d1f/);
});

test("defaults invalid or missing appearance settings to Home Assistant automatic theme", () => {
  const fallback = createCard({ theme_mode: "sepia", entities: {} });
  const missing = createCard({ entities: {} });
  assert.match(fallback, /data-theme="auto"/);
  assert.match(missing, /data-theme="auto"/);
});

test("promotes live SOC and odometer into the dashboard hero", () => {
  const html = createCard(
    { entities: { current_soc: "sensor.soc", odometer: "sensor.odo" } },
    {
      "sensor.soc": { state: "87.4", last_updated: "2026-11-23T10:00:00Z", attributes: {} },
      "sensor.odo": { state: "12345", last_updated: "2026-11-23T10:00:00Z", attributes: { unit_of_measurement: "km" } },
    },
  );
  assert.match(html, /live-hero vehicle-telemetry/);
  assert.match(html, /BATERÍA ACTUAL/);
  assert.match(html, /87,4/);
  assert.match(html, /KILOMETRAJE/);
  assert.match(html, /12\.345/);
});

test("shows only an explicitly configured range sensor and does not estimate range", () => {
  const configured = createCard(
    { entities: { range: "sensor.range" } },
    { "sensor.range": { state: "410", attributes: { unit_of_measurement: "km" } } },
  );
  const absent = createCard({ entities: { current_soc: "sensor.soc" } }, { "sensor.soc": { state: "80", attributes: {} } });
  assert.match(configured, /Autonomía indicada/);
  assert.match(configured, /410 km/);
  assert.doesNotMatch(absent, /Autonomía indicada/);
});

test("does not fabricate invalid live telemetry values", () => {
  const html = createCard(
    { entities: { current_soc: "sensor.soc", odometer: "sensor.odo" } },
    {
      "sensor.soc": { state: "140", attributes: {} },
      "sensor.odo": { state: "-1", attributes: {} },
    },
  );
  assert.match(html, /BATERÍA ACTUAL/);
  assert.match(html, /Odómetro no disponible/);
  assert.doesNotMatch(html, /140%/);
  assert.doesNotMatch(html, /-1 km/);
});
