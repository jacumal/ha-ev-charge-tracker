import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const source = readFileSync(
  new URL("../custom_components/ev_charge_tracker/frontend/ev-charge-tracker-card.js", import.meta.url),
  "utf8",
);

function createEditorInstance(config = {}) {
  const registry = new Map();
  class HTMLElement {}
  runInNewContext(source, {
    HTMLElement,
    customElements: { define: (name, constructor) => registry.set(name, constructor) },
    window: {},
    URL,
  });
  const Editor = registry.get("ev-charge-tracker-card-editor");
  const editor = new Editor();
  editor.setConfig(config);
  return editor;
}

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


test("editor exposes live vehicle identity, image and charge-port controls", () => {
  assert.match(source, /id="visual_brand"/);
  assert.match(source, /id="visual_model"/);
  assert.match(source, /id="visual_image"/);
  assert.match(source, /id="visual_port_x"/);
  assert.match(source, /id="visual_port_y"/);
  assert.match(source, /setCustomValidity/);
});

test("existing cards refresh their selected profile while retaining manual entity overrides", () => {
  assert.match(source, /_syncSelectedProfile/);
  assert.match(source, /window\.setInterval/);
  assert.match(source, /profile_manual_override/);
  assert.match(source, /vehicle_visual = profile\.vehicle_visual/);
});

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
      "sensor.leapmotor_precise_battery": { state: "87.4", last_updated: new Date().toISOString(), attributes: { unit_of_measurement: "%" } },
      "sensor.leapmotor_odometer": { state: "12345", last_updated: new Date().toISOString(), attributes: { unit_of_measurement: "km" } },
    },
  );
  assert.match(html, /BATERÍA ACTUAL/);
  assert.ok(html.includes("87,4<small>%</small>"));
  assert.match(html, /KILOMETRAJE/);
  assert.ok(html.includes("12.345"));
  assert.match(html, /<small>km<\/small>/);
  assert.match(html, /vehicle-telemetry/);
  assert.doesNotMatch(html, /Datos complementarios del vehículo/);
});

test("renders the official transparent C10 image and cable state without a custom image", () => {
  const html = createCard(
    { name: "Leapmotor C10", vehicle_visual: { visual_brand: "Leapmotor", visual_model: "C10", visual_color: "#AABBCC", visual_body_style: "suv" }, entities: { status: "sensor.status" } },
    { "sensor.status": { state: "idle", attributes: {} } },
  );
  assert.match(html, /vehicle-visual/);
  assert.match(html, /Leapmotor C10/);
  assert.ok(html.includes("https://www.leapmotor.net/_next/image"));
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
      "sensor.soc": { state: "87.4", last_updated: new Date().toISOString(), attributes: {} },
      "sensor.odo": { state: "12345", last_updated: new Date().toISOString(), attributes: { unit_of_measurement: "km" } },
    },
  );
  assert.match(html, /live-hero vehicle-telemetry/);
  assert.match(html, /BATERÍA ACTUAL/);
  assert.match(html, /87,4/);
  assert.match(html, /KILOMETRAJE/);
  assert.match(html, /12\.345/);
});


test("hides stale SOC and odometer readings instead of presenting obsolete values", () => {
  const staleAt = new Date(Date.now() - 181 * 60 * 1000).toISOString();
  const html = createCard(
    { entities: { current_soc: "sensor.soc", odometer: "sensor.odo" } },
    {
      "sensor.soc": { state: "87.4", last_updated: staleAt, attributes: {} },
      "sensor.odo": { state: "12345", last_updated: staleAt, attributes: { unit_of_measurement: "km" } },
    },
  );
  assert.match(html, /Batería no disponible/);
  assert.match(html, /Odómetro no disponible/);
  assert.doesNotMatch(html, /87,4/);
  assert.doesNotMatch(html, /12\.345/);
});

test("shows only an explicitly configured range sensor and does not estimate range", () => {
  const configured = createCard(
    { entities: { range: "sensor.range" } },
    { "sensor.range": { state: "410", last_updated: new Date().toISOString(), attributes: { unit_of_measurement: "km" } } },
  );
  const absent = createCard({ entities: { current_soc: "sensor.soc" } }, { "sensor.soc": { state: "80", attributes: {} } });
  assert.match(configured, /live-hero vehicle-telemetry with-range/);
  assert.match(configured, /AUTONOMÍA/);
  assert.match(configured, /410/);
  assert.doesNotMatch(absent, /AUTONOMÍA/);
});



test("rejects implausibly future-dated vehicle telemetry", () => {
  const futureAt = new Date(Date.now() + 60 * 60 * 1000).toISOString();
  const html = createCard(
    { entities: { current_soc: "sensor.soc" } },
    { "sensor.soc": { state: "88", last_updated: futureAt, attributes: {} } },
  );
  assert.match(html, /Batería no disponible/);
  assert.doesNotMatch(html, /88<small>%<\/small>/);
});

test("does not display unavailable source telemetry as a numeric reading", () => {
  const html = createCard(
    { entities: { current_soc: "sensor.soc", odometer: "sensor.odo" } },
    {
      "sensor.soc": { state: "unavailable", last_updated: new Date().toISOString(), attributes: {} },
      "sensor.odo": { state: "unknown", last_updated: new Date().toISOString(), attributes: {} },
    },
  );
  assert.match(html, /Batería no disponible/);
  assert.match(html, /Odómetro no disponible/);
  assert.doesNotMatch(html, /<small>%<\/small>/);
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


test("redesigned latest charge summary highlights delivered energy and SOC progression", () => {
  const html = createCard(
    { entities: { status: "sensor.status", energy: "sensor.energy", history: "sensor.history", cost: "sensor.cost", duration: "sensor.duration", soc_start: "sensor.start", soc_end: "sensor.end", soc_increase: "sensor.increase" } },
    {
      "sensor.status": { state: "completed", attributes: {} },
      "sensor.energy": { state: "24.6", attributes: { unit_of_measurement: "kWh" } },
      "sensor.cost": { state: "3.2", attributes: { cost_status: "complete", currency: "EUR" } },
      "sensor.duration": { state: "180", attributes: {} },
      "sensor.start": { state: "30", attributes: {} },
      "sensor.end": { state: "80", attributes: {} },
      "sensor.increase": { state: "50", attributes: {} },
      "sensor.history": { state: "1", attributes: { latest_session: { started_at: "2026-11-23T08:00:00Z", ended_at: "2026-11-23T11:00:00Z" }, sessions: [] } },
    },
  );
  assert.match(html, /session-energy/);
  assert.match(html, /24,6/);
  assert.match(html, /soc-progress/);
  assert.match(html, /Asignación de tarifa/);
});

test("redesigned history distinguishes partial cost and never plots invalid values as positive energy", () => {
  const html = createCard(
    { display_mode: "complete", entities: { history: "sensor.history" } },
    { "sensor.history": { state: "2", attributes: { sessions: [
      { started_at: "2026-11-22T10:00:00Z", energy_kwh: 10, known_cost: 1.2, cost: null, cost_status: "partial", soc_start: 40, soc_end: 65 },
      { started_at: "2026-11-21T10:00:00Z", energy_kwh: -5, cost: -2, cost_status: "unknown", soc_start: null, soc_end: null },
    ] } } },
  );
  assert.match(html, /row-energy/);
  assert.match(html, /Coste parcial/);
  assert.match(html, /cost-partial/);
  assert.match(html, /Progreso de batería no disponible/);
  assert.match(html, /row-main/);
});

test("editor forwards config changes to Lovelace and never claims persistence before native save", () => {
  const registry = new Map();
  class HTMLElement {
    dispatchEvent(event) { this.lastEvent = event; return true; }
  }
  class CustomEvent {
    constructor(type, options) { this.type = type; Object.assign(this, options); }
  }
  runInNewContext(source, {
    HTMLElement,
    CustomEvent,
    customElements: { define: (name, constructor) => registry.set(name, constructor) },
    window: {},
  });
  const Editor = registry.get("ev-charge-tracker-card-editor");
  const editor = new Editor();
  editor._config = { name: "Mi C10", entities: { status: "sensor.status" } };
  editor._fireConfigChanged();
  assert.equal(editor.lastEvent.type, "config-changed");
  assert.equal(editor.lastEvent.bubbles, true);
  assert.equal(editor.lastEvent.composed, true);
  assert.deepEqual(JSON.parse(JSON.stringify(editor.lastEvent.detail.config)), editor._config);
  assert.match(source, /Cambios enviados a Lovelace, pero aún pendientes de guardar/);
  assert.match(source, /no ofrece a esta tarjeta una confirmación fiable/);
});

function createCardInstance() {
  const registry = new Map();
  class HTMLElement {
    attachShadow() { this.shadowRoot = { innerHTML: "" }; return this.shadowRoot; }
  }
  runInNewContext(source, {
    HTMLElement,
    URL,
    customElements: { define: (name, constructor) => registry.set(name, constructor) },
    window: {},
  });
  const Card = registry.get("ev-charge-tracker-card");
  return new Card();
}

test("gallery choices are stored per vehicle and shared by that vehicle's charger profiles", () => {
  const editor = createEditorInstance({
    vehicle_visuals: {
      "leapmotor-c10": { visual_image: "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/C10.jpg/900px-C10.jpg" },
      "tesla-model-y": { visual_image: "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/ModelY.jpg/900px-ModelY.jpg" },
    },
  });
  const c10Home = { entry_id: "c10-home", vehicle_name: "C10 casa", charger_name: "Wallbox", vehicle_visual: { visual_brand: "Leapmotor", visual_model: "C10" }, entities: {} };
  const c10Work = { entry_id: "c10-work", vehicle_name: "C10 trabajo", charger_name: "AC", vehicle_visual: { visual_brand: "Leapmotor", visual_model: "C10" }, entities: {} };
  const tesla = { entry_id: "tesla-home", vehicle_name: "Tesla Model Y", charger_name: "Wallbox", vehicle_visual: { visual_brand: "Tesla", visual_model: "Model Y" }, entities: {} };

  editor._applyProfile(c10Home, false);
  assert.equal(editor._config.vehicle_visual.visual_image, editor._config.vehicle_visuals["leapmotor-c10"].visual_image);
  editor._applyProfile(c10Work, false);
  assert.equal(editor._config.vehicle_visual.visual_image, editor._config.vehicle_visuals["leapmotor-c10"].visual_image);
  editor._applyProfile(tesla, false);
  assert.equal(editor._config.vehicle_visual.visual_image, editor._config.vehicle_visuals["tesla-model-y"].visual_image);
  assert.notEqual(editor._profileVisualKey(c10Home), editor._profileVisualKey(tesla));
});

test("editor automatically suggests the selected vehicle identity for gallery searches", () => {
  assert.match(source, /const suggestedQuery = \[visual\.visual_brand, visual\.visual_model\]/);
  assert.match(source, /this\._galleryQueryEdited/);
  assert.match(source, /next\.vehicle_visuals = \{ \.\.\.\(next\.vehicle_visuals \|\| \{\}\), \[visualKey\]: \{ \.\.\.next\.vehicle_visual \} \}/);
});

test("vehicle image gallery is present and queries Commons with machine-readable license metadata", () => {
  assert.match(source, /Galería gratuita de vehículos/);
  assert.match(source, /https:\/\/commons\.wikimedia\.org\/w\/api\.php/);
  assert.match(source, /iiprop:"url\|extmetadata"/);
  assert.match(source, /LicenseShortName/);
  assert.match(source, /CC0/);
  assert.match(source, /Public domain/);
  assert.match(source, /CC BY-SA/);
});

test("only local images or HTTPS Wikimedia Commons uploads are accepted", () => {
  const card = createCardInstance();
  assert.equal(card._validVehicleImage("/local/ev-charge-tracker/c10.webp"), true);
  assert.equal(card._validVehicleImage("https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/C10.jpg/900px-C10.jpg"), true);
  assert.equal(card._validVehicleImage("http://upload.wikimedia.org/wikipedia/commons/a/a1/C10.jpg"), false);
  assert.equal(card._validVehicleImage("https://example.com/c10.jpg"), false);
  assert.equal(card._validVehicleImage("https://upload.wikimedia.org.evil.example/c10.jpg"), false);
  assert.equal(card._validVehicleImage("/local/ev-charge-tracker/../secret.png"), false);
});

test("selected Commons images retain creator, license and source-page attribution", () => {
  assert.match(source, /visual_image_credit/);
  assert.match(source, /visual_image_license/);
  assert.match(source, /visual_image_license_url/);
  assert.match(source, /visual_image_page/);
  assert.match(source, /visual_image_source/);
  assert.match(source, /vehicle-image-credit/);
  assert.match(source, /noopener noreferrer/);
});

test("autonomy gets its own telemetry column only when explicitly mapped", () => {
  const configured = createCard(
    { entities: { range: "sensor.range" } },
    { "sensor.range": { state: "282", last_updated: new Date().toISOString(), attributes: { unit_of_measurement: "km" } } },
  );
  const absent = createCard({ entities: {} });
  assert.match(configured, /live-hero vehicle-telemetry with-range/);
  assert.match(configured, /AUTONOMÍA/);
  assert.match(configured, /282/);
  assert.doesNotMatch(absent, /AUTONOMÍA/);
});

test("card links both image source and reusable license when attribution is available", () => {
  assert.match(source, /visual_image_license_url/);
  assert.match(source, /creativecommons/);
  assert.match(source, /noopener noreferrer/);
});

test("editor clears stale license attribution when a selected image is replaced manually", () => {
  assert.match(source, /delete next\.vehicle_visual\.visual_image_license_url/);
  assert.match(source, /const previousImage/);
});

test("Leapmotor C10 default cable anchor is on the rear-left quarter", () => {
  const html = createCard({
    vehicle_visual: { visual_brand: "Leapmotor", visual_model: "C10" },
    entities: {},
  });
  assert.match(html, /cx="216" cy="63"/);
});


test("editor image validation is available independently from the card class", () => {
  const editor = createEditorInstance();
  assert.equal(editor._validVehicleImage("/ev_charge_tracker/vehicle-images/leapmotor-c10-white.webp"), false);
  assert.equal(editor._validVehicleImage("/local/ev-charge-tracker/c10.webp"), true);
  assert.equal(editor._validVehicleImage("https://upload.wikimedia.org/wikipedia/commons/a/a1/C10.jpg"), true);
  assert.equal(editor._validVehicleImage("https://example.com/c10.jpg"), false);
  assert.equal(editor._validVehicleImage("https://www.leapmotor.net/_next/image?q=90&url=https%3A%2F%2Fwww.leapmotor.net%2Fimages%2Fdefault-source%2Fc10%2Fpearl-white-%2817%29.png%3Fsfvrsn%3Df11bcf73_36&w=3840"), true);
});

test("card uses the bundled C10 image when the selected vehicle identity names C10", () => {
  const html = createCard(
    { name: "Leapmotor C10", entities: {} },
    {},
  );
  assert.ok(html.includes("https://www.leapmotor.net/_next/image"));
});

test("card does not render the generic cartoon car when no vehicle image is configured", () => {
  const html = createCard({ name: "Mi vehículo", entities: {} }, {});
  assert.match(html, /Imagen del vehículo no disponible/);
  assert.doesNotMatch(html, /vehicle-body/);
});


test("editor preview derives the C10 default image from the selected profile identity", () => {
  assert.match(source, /const activeProfile = this\._profiles\.find\(item => item\.entry_id === this\._config\.profile_entry_id\)/);
  assert.match(source, /const identityText = \[visual\.visual_brand, visual\.visual_model, activeProfile\?\.vehicle_name, this\._config\.name\]/);
  assert.match(source, /const image = this\._validVehicleImage\(visual\.visual_image\) \? visual\.visual_image : \(isLeapmotorC10 \? DEFAULT_C10_IMAGE_URL/);
  assert.match(source, /preview\.innerHTML = '<div class="preview-stage">' \+ imageOrFallback/);
});


test("uses the same verified official transparent C10 image in card and editor", () => {
  assert.match(source, /DEFAULT_C10_IMAGE_URL/);
  assert.ok(source.includes("www.leapmotor.net/_next/image"));
  assert.match(source, /officialC10Image/);
  const html = createCard(
    { name: "Leap C10", vehicle_visual: { visual_brand: "Leapmotor", visual_model: "C10" }, entities: {} },
  );
  assert.ok(html.includes("www.leapmotor.net/_next/image"));
  assert.match(html, /vehicle-image custom/);
});

test("uses the approved vehicle-first layout and neutral image fallback", () => {
  assert.match(source, /grid-template-areas:"stage state"/);
  assert.match(source, /vehicle-subtitle/);
  assert.match(source, /history-summary/);
  assert.match(source, /Imagen del vehículo no disponible/);
});


test("migrates beta 7 legacy C10 image setting to the official default", () => {
  const html = createCard(
    { name: "Leapmotor C10", vehicle_visual: {
      visual_brand: "Leapmotor", visual_model: "C10",
      visual_image: "/ev_charge_tracker/vehicle-images/leapmotor-c10-white.webp",
    }, entities: {} },
  );
  assert.ok(html.includes("www.leapmotor.net/_next/image"));
  assert.doesNotMatch(html, /vehicle-images\/leapmotor-c10-white/);
});


test("deduplicates vehicle generation and model year in the hero subtitle", () => {
  const html = createCard(
    { name: "Leap C10", vehicle_visual: {
      visual_brand: "Leapmotor", visual_model: "C10",
      visual_generation: "2026", visual_year: "2026", visual_trim: "Design",
    }, entities: {} },
  );
  assert.ok(html.includes("Design · 2026"));
  assert.doesNotMatch(html, /2026 · 2026/);
});
