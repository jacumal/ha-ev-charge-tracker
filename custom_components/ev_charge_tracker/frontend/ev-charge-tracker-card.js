/* ChargeTrack Lovelace card
 * Copyright (c) ChargeTrack contributors. MIT.
 */
const CARD_VERSION = "0.6.0";
const DEFAULT_C10_IMAGE_URL = "/ev_charge_tracker/vehicle-images/leapmotor-c10-white.webp";
const VEHICLE_CATALOG = [
  ["leapmotor-c10","Leapmotor C10","Leapmotor","C10","suv","/ev_charge_tracker/vehicle-images/leapmotor-c10-white.webp"],
  ["leapmotor-b10","Leapmotor B10","Leapmotor","B10","suv",""],
  ["leapmotor-t03","Leapmotor T03","Leapmotor","T03","hatchback",""],
  ["tesla-model-y","Tesla Model Y","Tesla","Model Y","suv",""],
  ["tesla-model-3","Tesla Model 3","Tesla","Model 3","sedan",""],
  ["geely-galaxy-xingyuan","Geely Galaxy Xingyuan / EX2","Geely","Galaxy Xingyuan / EX2","hatchback",""],
  ["wuling-mini-ev","Wuling Hongguang Mini EV","Wuling","Hongguang Mini EV","hatchback",""],
  ["byd-seagull","BYD Seagull / Dolphin Surf","BYD","Seagull / Dolphin Surf","hatchback",""],
  ["xiaomi-su7","Xiaomi SU7","Xiaomi","SU7","sedan",""],
  ["byd-yuan-up","BYD Yuan UP / Atto 2","BYD","Yuan UP / Atto 2","suv",""],
  ["byd-dolphin","BYD Dolphin","BYD","Dolphin","hatchback",""],
  ["byd-yuan-plus","BYD Yuan Plus / Atto 3","BYD","Yuan Plus / Atto 3","suv",""],
  ["xpeng-mona-m03","XPeng Mona M03","XPeng","Mona M03","sedan",""],
  ["vw-id3","Volkswagen ID.3","Volkswagen","ID.3","hatchback",""],
  ["vw-id4","Volkswagen ID.4","Volkswagen","ID.4","suv",""],
  ["vw-id7","Volkswagen ID.7","Volkswagen","ID.7","sedan",""],
  ["skoda-enyaq","Škoda Enyaq","Škoda","Enyaq","suv",""],
  ["skoda-elroq","Škoda Elroq","Škoda","Elroq","suv",""],
  ["hyundai-kona-electric","Hyundai Kona Electric","Hyundai","Kona Electric","suv",""],
  ["hyundai-ioniq-5","Hyundai IONIQ 5","Hyundai","IONIQ 5","suv",""],
  ["kia-ev3","Kia EV3","Kia","EV3","suv",""],
  ["kia-ev6","Kia EV6","Kia","EV6","suv",""],
  ["kia-ev9","Kia EV9","Kia","EV9","suv",""],
  ["renault-5","Renault 5 E-Tech","Renault","5 E-Tech","hatchback",""],
  ["renault-megane","Renault Megane E-Tech","Renault","Megane E-Tech","hatchback",""],
  ["volvo-ex30","Volvo EX30","Volvo","EX30","suv",""],
  ["mg4","MG4 Electric","MG","4 Electric","hatchback",""],
  ["ford-mach-e","Ford Mustang Mach-E","Ford","Mustang Mach-E","suv",""],
  ["bmw-ix1","BMW iX1","BMW","iX1","suv",""],
  ["bmw-i4","BMW i4","BMW","i4","sedan",""],
].map(([id,label,brand,model,body,image]) => ({id,label,brand,model,body,image}));

class EVChargeTrackerCard extends HTMLElement {
  setConfig(config) {
    // Home Assistant calls setConfig with the stub while the user is still
    // configuring the card. Keep incomplete configurations editable.
    this.config = { ...config, entities: { ...(config?.entities || {}) } };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    // Home Assistant may assign hass after setConfig, before the shadow root
    // exists. _render creates the root when needed, so do not guard on it.
    if (this.config) this._render();
    this._syncSelectedProfile();
    if (this.config?.profile_entry_id && !this._profileSyncTimer && typeof window?.setInterval === "function") {
      this._profileSyncTimer = window.setInterval(() => this._syncSelectedProfile(true), 30000);
    }
  }

  disconnectedCallback() {
    if (this._profileSyncTimer && typeof window?.clearInterval === "function") {
      window.clearInterval(this._profileSyncTimer);
      this._profileSyncTimer = null;
    }
  }

  async _syncSelectedProfile(force = false) {
    const entryId = this.config?.profile_entry_id;
    if (!entryId || !this._hass || typeof this._hass.callWS !== "function" || this._profileSyncPromise) return;
    if (!force && this._profileSyncAt && Date.now() - this._profileSyncAt < 30000) return;
    this._profileSyncAt = Date.now();
    this._profileSyncPromise = this._hass.callWS({ type: "ev_charge_tracker/profiles" }).then(result => {
      const profile = (result?.profiles || []).find(item => item.entry_id === entryId);
      if (!profile || !this.config || this.config.profile_entry_id !== entryId) return;
      const next = { ...this.config, entities: { ...(this.config.entities || {}) } };
      if (!next.profile_manual_override) next.entities = { ...(profile.entities || {}) };
      if (!next.vehicle_visual_override) next.vehicle_visual = profile.vehicle_visual || next.vehicle_visual || {};
      this.config = next;
      this._render();
    }).catch(() => {
      // The card keeps its last known profile configuration while HA is offline.
    }).finally(() => {
      this._profileSyncPromise = null;
    });
  }

  getCardSize() { return 5; }

  _validVehicleImage(value) {
    if (typeof value !== "string" || value.includes("..")) return false;
    if (/^\/local\/ev-charge-tracker\/(?:custom\/)?[A-Za-z0-9_-][A-Za-z0-9._-]*\.(png|webp)$/i.test(value)) return true;
    try {
      const url = new URL(value);
      const commonsImage = url.protocol === "https:" && url.hostname === "upload.wikimedia.org" &&
        /^\/wikipedia\/commons\/(?:thumb\/)?[A-Za-z0-9_./%()-]+\.(?:png|webp|jpe?g)(?:\/[^?#]+)?$/i.test(url.pathname);
      return commonsImage;
    } catch { return false; }
  }

  _state(entityId) {
    return entityId && this._hass ? this._hass.states[entityId] : undefined;
  }

  _value(entityId, fallback = "—") {
    const state = this._state(entityId);
    if (!state || ["unknown", "unavailable", "none"].includes(state.state)) return fallback;
    return state.state;
  }

  _attr(entityId, key, fallback = undefined) {
    const state = this._state(entityId);
    return state && state.attributes && state.attributes[key] !== undefined ? state.attributes[key] : fallback;
  }

  _number(entityId) {
    const value = Number(this._value(entityId, NaN));
    return Number.isFinite(value) ? value : null;
  }

  _fmt(value, digits = 1) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
    return new Intl.NumberFormat(this._hass?.locale?.language || "es-ES", {
      maximumFractionDigits: digits,
    }).format(Number(value));
  }

  _date(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat(this._hass?.locale?.language || "es-ES", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    }).format(date);
  }

  _duration(minutes) {
    if (minutes === null) return "—";
    const total = Math.max(0, Math.round(minutes));
    const hours = Math.floor(total / 60);
    const mins = total % 60;
    return hours ? `${hours} h ${mins} min` : `${mins} min`;
  }

  _socRing(value, label) {
    const valid = value !== null && value >= 0 && value <= 100;
    const pct = valid ? value : 0;
    return `<div class="soc">
      <div class="ring" style="--pct:${pct}"><span>${valid ? this._fmt(value, 0) + "%" : "—"}</span></div>
      <div class="soc-label">${label}</div>
    </div>`;
  }

  _render() {
    if (!this.config || !this._hass) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const e = this.config.entities || {};
    const statusState = this._state(e.status);
    const status = !e.status
      ? "not_configured"
      : (!statusState || ["unknown", "unavailable", "none"].includes(statusState.state)
        ? "unavailable"
        : statusState.state);
    const statusLabels = {
      idle: "En espera", charging: "Cargando", finishing: "Finalizando",
      pending_finalization: "Pendiente de confirmar", completed: "Completada",
      needs_attention: "Revisar datos", not_configured: "Estado sin configurar",
      unavailable: "Estado no disponible",
    };
    const charging = status === "charging";
    const statusWarning = ["pending_finalization", "needs_attention", "not_configured", "unavailable"].includes(status);
    const energy = this._number(e.energy);
    const cost = this._number(e.cost);
    const rawKnownCost = this._attr(e.cost, "known_cost", null);
    const knownCost = rawKnownCost === null || rawKnownCost === undefined ? null : Number(rawKnownCost);
    const hasKnownCost = knownCost !== null && Number.isFinite(knownCost);
    const socStart = this._number(e.soc_start);
    const socEnd = this._number(e.soc_end);
    const increase = this._number(e.soc_increase);
    const currentSoc = this._number(e.current_soc);
    const odometer = this._number(e.odometer);
    const odometerUnit = this._attr(e.odometer, "unit_of_measurement", "km") || "km";
    const rangeValue = this._number(e.range);
    const rangeUnit = this._attr(e.range, "unit_of_measurement", "km") || "km";
    const sourceAgeMinutes = entityId => {
      const state = this._state(entityId);
      if (!state || ["unknown", "unavailable", "none"].includes(state.state)) return null;
      const timestamp = Date.parse(state.last_updated || state.last_changed || "");
      if (!Number.isFinite(timestamp)) return null;
      const age = (Date.now() - timestamp) / 60000;
      return age < -5 ? null : Math.max(0, age);
    };
    const socAgeMinutes = sourceAgeMinutes(e.current_soc);
    const odometerAgeMinutes = sourceAgeMinutes(e.odometer);
    const rangeAgeMinutes = sourceAgeMinutes(e.range);
    const validSoc = currentSoc !== null && currentSoc >= 0 && currentSoc <= 100 && socAgeMinutes !== null && socAgeMinutes <= 180;
    const validOdometer = odometer !== null && odometer >= 0 && odometerAgeMinutes !== null && odometerAgeMinutes <= 180;
    const validRange = rangeValue !== null && rangeValue >= 0 && rangeAgeMinutes !== null && rangeAgeMinutes <= 180;
    const hasRangeSensor = Boolean(e.range);
    const primaryAges = [e.current_soc ? socAgeMinutes : null, e.odometer ? odometerAgeMinutes : null].filter(age => age !== null);
    const telemetryAgeMinutes = primaryAges.length ? Math.max(...primaryAges) : null;
    const freshnessParts = [];
    if (e.current_soc) freshnessParts.push(validSoc ? (socAgeMinutes <= 15 ? "Batería actualizada" : "Batería antigua") : "Batería no disponible");
    if (e.odometer) freshnessParts.push(validOdometer ? (odometerAgeMinutes <= 15 ? "Odómetro actualizado" : "Odómetro antiguo") : "Odómetro no disponible");
    const telemetryFreshness = freshnessParts.join(" · ") || "Sin telemetría configurada";
    const hasLiveTelemetry = Boolean(e.current_soc || e.odometer || e.range);
    const displayMode = ["compact", "balanced", "complete"].includes(this.config.display_mode) ? this.config.display_mode : "balanced";
    const themeMode = ["auto", "light", "dark"].includes(this.config.theme_mode) ? this.config.theme_mode : "auto";
    const duration = this._number(e.duration);
    const history = this._attr(e.history, "sessions", []);
    const current = this._attr(e.history, "current_session", null);
    const latest = this._attr(e.history, "latest_session", null);
    const pluggedState = this._state(e.plugged);
    const hasPluggedSensor = Boolean(e.plugged);
    const hasPluggedReading = Boolean(
      pluggedState && !["unknown", "unavailable", "none"].includes(pluggedState.state)
    );
    const pluggedValue = hasPluggedReading ? String(pluggedState.state).toLowerCase() : "";
    const cableConnected = ["on", "true", "1", "connected", "plugged"].includes(pluggedValue);
    const cableDisconnected = ["off", "false", "0", "disconnected", "unplugged"].includes(pluggedValue);
    const inconsistentConnection = charging && hasPluggedReading && !cableConnected;
    const statusLabel = inconsistentConnection ? "Señales contradictorias" : (statusLabels[status] || status);
    const vehicle = this.config.vehicle_visual || {};
    const visualColor = /^#[0-9a-f]{6}$/i.test(vehicle.visual_color || "") ? vehicle.visual_color : "#71869A";
    const bodyStyle = ["suv", "sedan", "hatchback", "van", "pickup"].includes(vehicle.visual_body_style) ? vehicle.visual_body_style : "suv";
    const vehicleIdentityText = [
      vehicle.visual_brand, vehicle.visual_model, this.config.vehicle_name,
      this.config.vehicle, this.config.name,
    ].filter(Boolean).join(" ");
    const isLeapmotorC10 = /c10/i.test(vehicle.visual_model || vehicleIdentityText) &&
      (!vehicle.visual_brand || /leapmotor/i.test(vehicle.visual_brand));
    const usingDefaultC10Image = isLeapmotorC10 && !this._validVehicleImage(vehicle.visual_image);
    const customImage = this._validVehicleImage(vehicle.visual_image) ? vehicle.visual_image : (isLeapmotorC10 ? DEFAULT_C10_IMAGE_URL : "");
    const imageCredit = vehicle.visual_image_credit || (usingDefaultC10Image ? "Leapmotor" : "");
    const imageLicense = vehicle.visual_image_license || "";
    const imageLicenseUrl = typeof vehicle.visual_image_license_url === "string" && /^https:\/\/creativecommons\.org\/(?:licenses|publicdomain)\//i.test(vehicle.visual_image_license_url) ? vehicle.visual_image_license_url : "";
    const imagePage = typeof vehicle.visual_image_page === "string" && /^https:\/\/commons\.wikimedia\.org\/wiki\//i.test(vehicle.visual_image_page) ? vehicle.visual_image_page : (usingDefaultC10Image ? "https://www.leapmotor.net/en-ie/other-products/offers/other-products-offers-offers-for-private-customers/c10---design---hybrid-ev-28_4kwh" : "");
    const defaultPortX = isLeapmotorC10 ? 83 : 67;
    const defaultPortY = isLeapmotorC10 ? 57 : 44;
    const portXValue = vehicle.visual_port_x == null || vehicle.visual_port_x === "" ? defaultPortX : Number(vehicle.visual_port_x);
    const portYValue = vehicle.visual_port_y == null || vehicle.visual_port_y === "" ? defaultPortY : Number(vehicle.visual_port_y);
    const portX = Math.round((Number.isFinite(portXValue) ? Math.min(100, Math.max(0, portXValue)) : 67) * 2.6);
    const portY = Math.round((Number.isFinite(portYValue) ? Math.min(100, Math.max(0, portYValue)) : 44) * 1.1);
    const cablePath = "M" + portX + " " + portY + " C" +
      Math.min(250, portX + 37) + " " + Math.max(0, portY - 3) + " " +
      Math.min(250, portX + 16) + " 91 236 91";
    const lastChargeCompleted = Boolean(
      !current && latest && (latest.status === "completed" || latest.completed_at || latest.ended_at)
    );
    const visualState = statusWarning || inconsistentConnection ? "error" : charging ? "charging" :
      (hasPluggedReading && cableConnected ? "connected" :
      ((status === "completed" || lastChargeCompleted) ? "completed" :
      (hasPluggedReading && cableDisconnected ? "disconnected" : "unknown")));
    const visualStateLabels = {
      disconnected: "Cable desconectado",
      unknown: hasPluggedSensor ? "Conexión no disponible" : "Conexión sin monitorizar",
      connected: lastChargeCompleted ? "Carga finalizada · Cable conectado" : "Cable conectado · En espera",
      charging: "Cargando · Flujo de energía activo",
      completed: "Carga finalizada",
      error: inconsistentConnection ? "Carga activa con cable desconectado" : "Estado que requiere atención",
    };
    const vehicleLabel = [vehicle.visual_brand, vehicle.visual_model].filter(Boolean).join(" ") ||
      this.config.vehicle_name || this.config.vehicle || this.config.name || "ChargeTrack";
    const vehicleDetails = [...new Set([vehicle.visual_trim, vehicle.visual_year, vehicle.visual_generation].filter(Boolean))].join(" · ");
    const bodyPaths = {
      suv: "M24 65 L32 45 Q36 39 48 37 L66 22 Q72 17 88 17 L151 17 Q163 17 171 27 L190 43 Q204 47 211 56 L216 70 L209 78 L24 78 Z",
      sedan: "M22 65 L31 49 Q36 43 52 41 L76 25 Q83 20 99 20 L151 22 Q165 23 174 35 L194 45 Q207 49 214 61 L214 77 L22 77 Z",
      hatchback: "M25 65 L34 45 Q40 39 56 37 L73 22 Q80 17 97 17 L147 18 Q160 19 169 32 L190 43 Q207 49 213 62 L213 77 L25 77 Z",
      van: "M23 64 L31 34 Q34 27 45 25 L174 25 Q188 25 196 39 L212 54 L215 77 L23 77 Z",
      pickup: "M22 62 L32 43 Q37 36 53 35 L72 21 L132 21 L145 37 L187 37 L208 54 L214 77 L22 77 Z",
    };
    const fallbackMarkup = '<div class="vehicle-image fallback" role="img" aria-label="' +
      this._escape(vehicleLabel) + '"><span>Imagen del vehículo no disponible</span></div>';
    const vehicleMarkup = '<div class="vehicle-visual">' +
      '<div class="vehicle-stage state-' + visualState + '" style="--vehicle-color:' + visualColor + '">' +
      (customImage
        ? '<img class="vehicle-image custom" src="' + this._escape(customImage) + '" alt="' + this._escape(vehicleLabel) + '" loading="lazy">'
        : fallbackMarkup) +
      '<svg class="cable-overlay" viewBox="0 0 260 110" aria-hidden="true">' +
        '<path class="cable-shadow" d="' + cablePath + '"/>' +
        '<path class="cable-line" d="' + cablePath + '"/>' +
        '<path class="energy-line" d="' + cablePath + '"/>' +
        '<g class="connector connector-free" transform="translate(232 82) rotate(8)"><rect x="0" y="0" width="15" height="18" rx="4"/><path d="M5 0 V-5 M10 0 V-5"/></g>' +
        '<g class="connector connector-plug" transform="translate(' + (portX - 8) + ' ' + (portY - 18) + ') rotate(90)"><rect x="0" y="0" width="15" height="18" rx="4"/><path d="M5 0 V-5 M10 0 V-5"/></g>' +
        '<circle class="charge-port" cx="' + portX + '" cy="' + portY + '" r="4"/>' +
      '</svg></div><div class="vehicle-state"><i></i>' + this._escape(visualStateLabels[visualState]) + '</div>' +
      (imageCredit && (imageLicense || imagePage) ? '<div class="vehicle-image-credit">Imagen: ' + (imagePage ? '<a href="' + this._escape(imagePage) + '" target="_blank" rel="noopener noreferrer">' : '') + this._escape(imageCredit) + (imagePage ? '</a>' : '') + (imageLicense ? ' · ' : '') + (imageLicenseUrl ? '<a href="' + this._escape(imageLicenseUrl) + '" target="_blank" rel="noopener noreferrer">' + this._escape(imageLicense) + '</a>' : this._escape(imageLicense)) + '</div>' : '') +
      '</div>';
    const diagnostic = this._attr(e.history, "diagnostic", "");
    const record = current || latest || {};
    const currency = this._attr(e.cost, "currency", this._state(e.cost)?.attributes?.unit_of_measurement || "EUR");
    const costStatus = this._attr(e.cost, "cost_status", record.cost_status || "unknown");
    const tariffEstimated = this._attr(e.cost, "tariff_estimated", record.tariff_estimated || false);
    const tariffBreakdown = this._attr(e.cost, "tariff_breakdown", record.tariff_breakdown || {});
    const hasTariffData = Boolean(
      this._state(e.cost) &&
      (cost !== null || hasKnownCost || (tariffBreakdown && Object.keys(tariffBreakdown).length))
    );
    const energyUnit = this._attr(e.energy, "unit_of_measurement", "kWh");
    const title = this.config.name || this.config.vehicle || "ChargeTrack";
    const start = this._date(record.started_at);
    const end = this._date(record.ended_at || record.completed_at);
    const maxHistory = Math.min(50, Math.max(1, Math.trunc(Number(this.config.max_history) || 8)));
    const allSessions = Array.isArray(history) ? history : [];
    const rows = allSessions.slice(0, maxHistory);
    const completedSessions = allSessions;
    const totalHistoryEnergy = completedSessions.reduce((sum, item) => {
      const value = Number(item.energy_kwh);
      return item.energy_kwh != null && Number.isFinite(value) && value >= 0 ? sum + value : sum;
    }, 0);
    const fullyPricedSessions = completedSessions.filter(item =>
      item.cost != null && Number.isFinite(Number(item.cost)) && Number(item.cost) >= 0 &&
      item.cost_status !== "partial" && item.cost_status !== "unknown"
    );
    const totalHistoryCost = fullyPricedSessions.reduce((sum, item) => sum + Number(item.cost), 0);
    const pricedHistoryEnergy = fullyPricedSessions.reduce((sum, item) => {
      const value = Number(item.energy_kwh);
      return item.energy_kwh != null && Number.isFinite(value) && value > 0 ? sum + value : sum;
    }, 0);
    const averageHistoryCost = pricedHistoryEnergy > 0 ? totalHistoryCost / pricedHistoryEnergy : null;
    const historyBars = completedSessions.slice(0, 8).reverse().filter(item =>
      item.energy_kwh != null && Number.isFinite(Number(item.energy_kwh)) && Number(item.energy_kwh) >= 0
    );
    const maxHistoryBar = Math.max(1, ...historyBars.map(item => Number(item.energy_kwh)));
    const recentRows = Array.isArray(history) ? history.slice(0, 8).slice().reverse() : [];
    const chartRows = recentRows.filter(item => item.energy_kwh != null && item.energy_kwh !== "" && Number.isFinite(Number(item.energy_kwh)) && Number(item.energy_kwh) >= 0);
    const maxEnergy = Math.max(1, ...chartRows.map(item => Number(item.energy_kwh)));
    // Cost history is independent of energy display: a known cost can still
    // be useful when the energy reading for that session is unavailable.
    const costRows = recentRows.filter(item => {
      const value = item.cost ?? item.known_cost;
      return value != null && value !== "" && Number.isFinite(Number(value)) && Number(value) >= 0;
    });
    const maxCost = Math.max(1, ...costRows.map(item => Number(item.cost ?? item.known_cost)));

    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; color:var(--primary-text-color); }
        ha-card { overflow:hidden; border-radius:var(--ha-card-border-radius, 22px); }
        .wrap { padding:20px; background:var(--ha-card-background,var(--card-background-color)); color:var(--primary-text-color); }
        .wrap[data-theme="dark"] { --primary-text-color:#f5f5f7; --secondary-text-color:#a1a1a6; --card-background-color:#1c1c1e; --secondary-background-color:#2c2c2e; --divider-color:#3a3a3c; --primary-color:#0a84ff; --success-color:#30d158; --warning-color:#ff9f0a; --ha-card-background:#1c1c1e; color-scheme:dark; }
        .wrap[data-theme="light"] { --primary-text-color:#1d1d1f; --secondary-text-color:#6e6e73; --card-background-color:#ffffff; --secondary-background-color:#f5f5f7; --divider-color:#d2d2d7; --primary-color:#007aff; --success-color:#28a745; --warning-color:#c77c00; --ha-card-background:#ffffff; color-scheme:light; }
        .top { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
        .eyebrow { color:var(--secondary-text-color); font-size:11px; font-weight:700; letter-spacing:.13em; text-transform:uppercase; }
        h2 { margin:5px 0 0; font-size:clamp(22px,4vw,30px); font-weight:700; letter-spacing:-.04em; }
        .vehicle-subtitle{margin-top:3px;color:var(--secondary-text-color);font-size:13px}
        .status { display:inline-flex; align-items:center; gap:7px; border-radius:30px; padding:7px 11px; background:var(--secondary-background-color); color:var(--secondary-text-color); font-size:12px; white-space:nowrap; }
        .dot { width:7px; height:7px; border-radius:50%; background:var(--success-color,#43a66b); }
        .status.active .dot { background:var(--state-active-color,var(--primary-color)); }
        .status.warn .dot { background:var(--warning-color,#d69b32); }
        .vehicle-visual { display:grid; grid-template-columns:minmax(0,1fr) 108px; grid-template-areas:"stage state"; align-items:center; gap:10px; margin-top:8px; padding:0 4px; min-width:0; }
        .vehicle-stage { grid-area:stage; position:relative; min-width:0; width:100%; height:clamp(180px,34vw,270px); }
        .vehicle-image.fallback { display:grid; place-items:center; color:var(--secondary-text-color); font-size:12px; text-align:center; }
        .vehicle-image.fallback span { padding:12px 18px; border:1px dashed var(--divider-color); border-radius:14px; }
        .vehicle-image { position:absolute; inset:0; width:100%; height:100%; object-fit:contain; }
        .vehicle-image-credit{margin-top:3px;color:var(--secondary-text-color);font-size:10px;line-height:1.35}
        .vehicle-image-credit a{color:inherit;text-decoration:underline}
        .cable-overlay { position:absolute; inset:0; width:100%; height:100%; overflow:visible; }
        .cable-shadow,.cable-line,.energy-line { fill:none; stroke-linecap:round; }
        .cable-shadow { stroke:var(--primary-text-color); stroke-width:5; opacity:.16; }
        .cable-line { stroke:var(--secondary-text-color); stroke-width:3; }
        .energy-line { stroke:var(--success-color,#42a66b); stroke-width:3; stroke-dasharray:5 8; opacity:0; }
        .connector { transition:opacity .25s ease; }
        .connector rect { fill:var(--secondary-text-color); stroke:var(--card-background-color); stroke-width:1.5; }
        .connector path { stroke:var(--secondary-text-color); stroke-width:2; }
        .connector-plug { opacity:0; }
        .state-connected .connector-free,.state-charging .connector-free { opacity:0; }
        .state-connected .connector-plug,.state-charging .connector-plug { opacity:1; }
        .charge-port { fill:var(--secondary-background-color); stroke:var(--secondary-text-color); stroke-width:2; }
        .state-disconnected .cable-line,.state-disconnected .cable-shadow,.state-disconnected .connector-free,.state-disconnected .energy-line,.state-disconnected .charge-port,.state-unknown .cable-line,.state-unknown .cable-shadow,.state-unknown .connector-free,.state-unknown .energy-line,.state-unknown .charge-port { opacity:.22; }
        .state-connected .cable-line,.state-connected .connector-plug,.state-connected .charge-port { opacity:1; }
        .state-charging .energy-line { opacity:1; animation:energy-flow 1s linear infinite; }
        .state-charging .cable-line { stroke:var(--success-color,#42a66b); }
        .state-completed .energy-line { opacity:0; }
        .state-completed .charge-port { fill:var(--success-color,#42a66b); }
        .state-error .cable-line,.state-error .connector,.state-error .charge-port { stroke:var(--warning-color,#d69b32); }
        .vehicle-state { grid-area:state; display:flex; align-items:center; gap:6px; max-width:108px; color:var(--secondary-text-color); font-size:11px; line-height:1.35; margin:0; padding:8px 9px; border-radius:18px; background:var(--secondary-background-color); white-space:normal; }
        .vehicle-state i { width:6px; height:6px; flex:0 0 6px; border-radius:50%; background:var(--secondary-text-color); }
        .state-charging + .vehicle-state i { background:var(--success-color,#42a66b); }
        .state-error + .vehicle-state i { background:var(--warning-color,#d69b32); }
        @keyframes energy-flow { to { stroke-dashoffset:-26; } }
        @media(prefers-reduced-motion:reduce) { .state-charging .energy-line { animation:none; opacity:.8; } .connector,.battery-track span { transition:none!important; } }
        .vehicle-telemetry{display:flex;justify-content:flex-end;gap:18px;margin:10px 4px 0;color:var(--secondary-text-color);font-size:11px}
        .vehicle-telemetry span{display:flex;gap:6px;align-items:baseline}.vehicle-telemetry small{font-size:10px}.vehicle-telemetry b{color:var(--primary-text-color);font-weight:650;font-variant-numeric:tabular-nums}
        .mode-compact .metrics .metric:nth-child(n+5),.mode-compact .dates{display:none}.mode-balanced .metrics .metric:nth-child(n+5){display:none}
        .live-hero { display:grid; grid-template-columns:minmax(0,1fr) 1px minmax(0,1fr); gap:18px; align-items:center; margin-top:16px; padding:20px; border-radius:22px; background:linear-gradient(135deg,color-mix(in srgb,var(--primary-color) 10%,var(--card-background-color)),var(--secondary-background-color) 72%); border:1px solid color-mix(in srgb,var(--primary-color) 12%,transparent); }
        .live-hero.with-range{grid-template-columns:minmax(0,1fr) 1px minmax(0,1fr) 1px minmax(0,1fr);gap:12px}
        .live-range-column{min-width:0}.live-range-column .odo-reading{font-size:clamp(20px,4vw,29px)}
        @media(max-width:520px){.live-hero.with-range{gap:8px;padding:12px}.live-hero.with-range .odo-reading{font-size:19px}.live-hero.with-range .live-label{font-size:8px}.live-hero.with-range .live-foot{font-size:9px}}
        .live-battery,.live-odometer { min-width:0; }
        .live-label { color:var(--secondary-text-color); font-size:10px; font-weight:750; letter-spacing:.14em; }
        .live-reading { margin-top:5px; font-size:clamp(34px,7vw,48px); line-height:1.05; font-weight:760; letter-spacing:-.065em; font-variant-numeric:tabular-nums; }
        .live-reading small { margin-left:3px; font-size:.48em; font-weight:650; letter-spacing:-.02em; }
        .battery-track { height:7px; margin-top:13px; overflow:hidden; border-radius:10px; background:color-mix(in srgb,var(--primary-text-color) 12%,transparent); }
        .battery-track span { display:block; height:100%; border-radius:inherit; background:var(--success-color,var(--primary-color)); transition:width .55s cubic-bezier(.2,.8,.2,1); }
        .live-divider { width:1px; height:62px; background:var(--divider-color); }
        .odo-reading { margin-top:9px; overflow-wrap:anywhere; font-size:clamp(22px,5vw,31px); line-height:1.12; font-weight:730; letter-spacing:-.055em; font-variant-numeric:tabular-nums; }
        .odo-reading small { font-size:13px; color:var(--secondary-text-color); font-weight:600; letter-spacing:0; }
        .live-foot { margin-top:9px; color:var(--secondary-text-color); font-size:10px; line-height:1.35; }
        .live-range { margin-top:8px; color:var(--secondary-text-color); font-size:11px; }
        .telemetry-freshness { display:flex; align-items:center; gap:6px; margin-top:9px; color:var(--secondary-text-color); font-size:10px; }
        .telemetry-freshness i { width:6px; height:6px; border-radius:50%; background:var(--success-color); }
        .telemetry-freshness.stale i { background:var(--warning-color); }
        .telemetry-freshness.missing i { background:var(--secondary-text-color); }
        .latest,.chart-card { border:1px solid color-mix(in srgb,var(--divider-color) 65%,transparent); }
        .section-title { font-size:11px; letter-spacing:.1em; text-transform:uppercase; font-weight:750; color:var(--secondary-text-color); }
        .history-head { margin-top:22px; padding-top:16px; border-top:1px solid var(--divider-color); }
        .latest { margin-top:20px; padding:18px; border-radius:20px; background:var(--secondary-background-color); }
        .charts { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin-top:18px; }
        .chart-card { min-width:0; padding:14px; border-radius:17px; background:var(--secondary-background-color); }
        .chart-title { display:flex; justify-content:space-between; gap:8px; align-items:baseline; font-size:12px; font-weight:700; }
        .chart-subtitle { color:var(--secondary-text-color); font-size:10px; font-weight:400; }
        .bars { display:flex; align-items:flex-end; gap:6px; height:94px; margin-top:13px; padding:0 2px; border-bottom:1px solid var(--divider-color); }
        .bar-wrap { flex:1; min-width:0; height:100%; display:flex; flex-direction:column; justify-content:flex-end; align-items:center; gap:5px; }
        .bar { width:min(100%,22px); min-height:3px; border-radius:6px 6px 2px 2px; background:var(--primary-color); opacity:.82; }
        .bar.cost { background:var(--success-color,var(--primary-color)); }
        .bar-label { max-width:100%; overflow:hidden; color:var(--secondary-text-color); font-size:9px; white-space:nowrap; text-overflow:ellipsis; }
        .chart-empty { display:flex; align-items:center; justify-content:center; height:94px; color:var(--secondary-text-color); font-size:12px; text-align:center; }
        .chart-legend { margin-top:8px; color:var(--secondary-text-color); font-size:10px; }
        .section-title { font-size:12px; color:var(--secondary-text-color); font-weight:650; letter-spacing:.04em; text-transform:uppercase; }
        .rings { display:flex; justify-content:space-around; align-items:center; gap:10px; padding:18px 0 14px; }
        .soc { display:flex; flex-direction:column; align-items:center; gap:8px; min-width:85px; }
        .ring { width:82px; height:82px; border-radius:50%; display:grid; place-items:center; background:conic-gradient(var(--primary-color) calc(var(--pct)*1%),var(--divider-color) 0); position:relative; }
        .ring:before { content:""; position:absolute; inset:6px; border-radius:50%; background:var(--secondary-background-color); }
        .ring span { z-index:1; font-size:21px; font-weight:700; letter-spacing:-.04em; }
        .soc-label { font-size:12px; color:var(--secondary-text-color); }
        .metrics { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:9px; }
        .metric { min-width:0; padding:12px 10px; border-radius:13px; background:var(--card-background-color); }
        .metric strong { display:block; font-size:19px; font-weight:680; letter-spacing:-.04em; overflow-wrap:anywhere; }
        .metric span { display:block; margin-top:4px; color:var(--secondary-text-color); font-size:11px; }
        .dates { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:14px; }
        .date { font-size:12px; color:var(--secondary-text-color); line-height:1.5; }
        .date b { display:block; color:var(--primary-text-color); font-weight:550; }
        .history-head { display:flex; justify-content:space-between; align-items:center; margin:22px 0 10px; }
        .history-head h3 { margin:0; font-size:15px; font-weight:650; }
        .count { color:var(--secondary-text-color); font-size:12px; }
        .row { display:grid; grid-template-columns:minmax(0,1.4fr) minmax(0,.8fr) minmax(0,.8fr); gap:8px; align-items:center; padding:12px 2px; border-top:1px solid var(--divider-color); }
        .row-date { font-size:13px; font-weight:600; }
        .row-sub { margin-top:3px; font-size:11px; color:var(--secondary-text-color); }
        .row-value { text-align:right; font-size:13px; font-weight:600; white-space:nowrap; }
        .row-value small { display:block; margin-top:3px; color:var(--secondary-text-color); font-size:10px; font-weight:400; }
        .empty { padding:18px 4px; color:var(--secondary-text-color); font-size:13px; }
        .diagnostic { margin-top:13px; color:var(--secondary-text-color); font-size:11px; line-height:1.4; }
        @media(max-width:520px) { .charts{grid-template-columns:1fr;gap:9px}.chart-card{padding:12px}.bars{height:78px}.live-hero{gap:12px;padding:16px}.live-reading{font-size:36px}.odo-reading{font-size:23px} }
        @media(max-width:520px) { .vehicle-visual{gap:8px;padding:8px}.vehicle-caption{flex-basis:36%}.vehicle-stage{height:76px}.vehicle-state{font-size:9px} }
        @media(max-width:420px) { .row{grid-template-columns:minmax(0,1fr);gap:8px}.row-stats{justify-content:space-between}.row-value{text-align:left}.row-energy{grid-column:1}.wrap{padding:15px}.ring{width:72px;height:72px}.ring span{font-size:19px}.metric{padding:10px 8px}.metric strong{font-size:17px}.row{grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr) minmax(0,.8fr)}.vehicle-caption{flex-basis:40%}.vehicle-stage{height:68px}.vehicle-state{font-size:8px}.live-hero{padding:14px;gap:10px}.live-reading{font-size:31px}.odo-reading{font-size:20px}.live-label{font-size:9px} }
        .latest { margin-top:20px; padding:18px; border:1px solid color-mix(in srgb,var(--divider-color) 65%,transparent); border-radius:22px; background:linear-gradient(155deg,var(--secondary-background-color),color-mix(in srgb,var(--card-background-color) 78%,var(--secondary-background-color))); }
        .latest-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.latest-heading .section-title{margin-bottom:5px}.session-state{font-size:10px;font-weight:700;letter-spacing:.04em;padding:5px 9px;border-radius:20px;background:color-mix(in srgb,var(--success-color) 13%,var(--card-background-color));color:var(--success-color)}
        .session-energy{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin:15px 0 4px}.session-energy strong{font-size:clamp(28px,6vw,38px);line-height:1;font-weight:760;letter-spacing:-.06em;font-variant-numeric:tabular-nums}.session-energy strong small{font-size:13px;letter-spacing:0;color:var(--secondary-text-color)}.session-energy span{font-size:10px;color:var(--secondary-text-color);text-align:right}
        .soc-progress{height:9px;border-radius:20px;overflow:hidden;background:var(--divider-color);margin:12px 0 16px}.soc-progress span{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,var(--primary-color),var(--success-color))}
        .session-footnote{margin-top:10px;font-size:10px;color:var(--secondary-text-color);line-height:1.4}
        .history-head{display:flex;justify-content:space-between;align-items:center;margin:24px 0 12px;padding-top:17px;border-top:1px solid var(--divider-color)}.history-head h3{margin:0;font-size:15px;font-weight:700}.count{font-size:11px;color:var(--secondary-text-color);padding:4px 8px;border-radius:20px;background:var(--secondary-background-color)}
        .history-summary{display:grid;grid-template-columns:minmax(0,1fr) minmax(90px,.55fr);gap:12px;align-items:end;padding:14px 12px;margin:0 0 12px;border:1px solid color-mix(in srgb,var(--divider-color) 65%,transparent);border-radius:17px;background:var(--secondary-background-color)}
        .history-summary-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
        .history-summary-stats span{display:block;color:var(--secondary-text-color);font-size:10px;line-height:1.3}
        .history-summary-stats strong{display:block;margin-top:5px;font-size:clamp(12px,2.2vw,17px);font-weight:700;overflow-wrap:anywhere}
        .history-sparkline{display:flex;align-items:end;justify-content:flex-end;gap:6px;height:62px;padding:0 2px}
        .history-sparkline i{display:block;flex:1;max-width:18px;min-width:5px;border-radius:4px 4px 1px 1px;background:color-mix(in srgb,var(--success-color) 60%,var(--card-background-color))}
        @media(max-width:520px){.history-summary{grid-template-columns:1fr}.history-sparkline{height:42px;justify-content:flex-start}.history-sparkline i{max-width:24px}}
        .row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px 14px;align-items:center;padding:13px 14px;margin:8px 0;border:1px solid color-mix(in srgb,var(--divider-color) 65%,transparent);border-radius:15px;background:var(--secondary-background-color)}
        .row-main{min-width:0}.row-date{font-size:12px;font-weight:700}.row-sub{margin-top:4px;font-size:10px;color:var(--secondary-text-color)}.row-stats{display:flex;gap:14px;justify-content:flex-end}.row-value{text-align:right;font-size:13px;font-weight:700;white-space:nowrap}.row-value small{display:block;margin-top:3px;color:var(--secondary-text-color);font-size:9px;font-weight:500}.row-energy{grid-column:1/-1;height:3px;border-radius:5px;background:var(--divider-color);overflow:hidden}.row-energy span{display:block;height:100%;background:var(--primary-color);border-radius:inherit}.cost-partial{color:var(--warning-color)!important}.history-empty{padding:24px 16px;text-align:center;border:1px dashed var(--divider-color);border-radius:15px;color:var(--secondary-text-color);font-size:12px;line-height:1.5}
        .chart-card{border-radius:19px;background:linear-gradient(155deg,var(--secondary-background-color),color-mix(in srgb,var(--card-background-color) 84%,var(--secondary-background-color)));box-shadow:inset 0 1px color-mix(in srgb,var(--primary-text-color) 4%,transparent)}
        .chart-title{font-size:12px;font-weight:750;letter-spacing:-.01em}.chart-subtitle{font-size:10px;color:var(--secondary-text-color)}
        .bars{height:104px;gap:8px;border-bottom:0;padding:8px 4px 0;background:repeating-linear-gradient(to bottom,transparent 0,transparent 24px,color-mix(in srgb,var(--divider-color) 55%,transparent) 25px)}
        .bar{width:min(100%,24px);border-radius:7px 7px 3px 3px;background:linear-gradient(180deg,var(--primary-color),color-mix(in srgb,var(--primary-color) 58%,var(--secondary-background-color)));box-shadow:0 2px 8px color-mix(in srgb,var(--primary-color) 15%,transparent)}
        .bar.cost{background:linear-gradient(180deg,var(--success-color),color-mix(in srgb,var(--success-color) 55%,var(--secondary-background-color)))}
        .chart-legend{padding-top:8px;border-top:1px solid var(--divider-color);line-height:1.4}
        /* Beta 8: vehicle-led composition from the approved ChargeTrack reference. */
        .vehicle-visual{grid-template-columns:minmax(0,1fr) 90px;grid-template-areas:"stage state";gap:8px;margin-top:8px;padding:0 4px;align-items:center}
        .vehicle-stage{height:clamp(175px,36vw,250px);min-height:160px}
        .vehicle-state{max-width:90px;font-size:10px;padding:7px 8px}
        .vehicle-image-credit{grid-column:1/-1;grid-area:auto;text-align:right;font-size:9px}
        .vehicle-image{object-fit:contain;object-position:center}
        .latest{margin-top:12px}
        .metrics{grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}
        .metric{padding:12px 9px;border-radius:16px}
        .metric strong{font-size:clamp(14px,2.4vw,19px)}
        .metric span{font-size:10px;line-height:1.35}
        .charts{margin-top:14px}
        @media(max-width:600px){.vehicle-visual{grid-template-columns:minmax(0,1fr) 82px}.vehicle-stage{height:190px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.metric:last-child{grid-column:span 2}.live-hero{padding:15px;gap:12px}.vehicle-state{max-width:82px;font-size:9px;padding:7px 6px}}
        @media(max-width:390px){.vehicle-stage{height:165px}.live-reading{font-size:30px}}
      </style>
      <ha-card>
        <div class="wrap" data-theme="${themeMode}">
          <div class="top">
            <div><div class="eyebrow">Cargas · Última carga</div><h2>${this._escape(vehicleLabel)}</h2>${vehicleDetails ? `<div class="vehicle-subtitle">${this._escape(vehicleDetails)}</div>` : ""}</div>
            <div class="status ${charging && !inconsistentConnection ? "active" : (statusWarning || inconsistentConnection) ? "warn" : ""}">
              <i class="dot"></i>${this._escape(statusLabel)}
            </div>
          </div>
          ${vehicleMarkup}
          ${hasLiveTelemetry ? `<section class="live-hero vehicle-telemetry ${hasRangeSensor ? "with-range" : ""}" aria-label="Telemetría actual del vehículo">
            <div class="live-battery">
              <div class="live-label">BATERÍA ACTUAL</div>
              <div class="live-reading">${validSoc ? this._fmt(currentSoc,1) + "<small>%</small>" : "—"}</div>
              <div class="battery-track"><span style="width:${validSoc ? currentSoc : 0}%"></span></div>
            </div>
            <div class="live-divider" aria-hidden="true"></div>
            ${hasRangeSensor ? `<div class="live-range-column"><div class="live-label">AUTONOMÍA</div><div class="odo-reading">${validRange ? this._fmt(rangeValue,0) : "—"} <small>${this._escape(rangeUnit)}</small></div><div class="live-foot">${validRange ? "Indicada por el vehículo" : "Autonomía no disponible"}</div></div><div class="live-divider" aria-hidden="true"></div>` : ""}
            <div class="live-odometer">
              <div class="live-label">KILOMETRAJE</div>
              <div class="odo-reading">${validOdometer ? this._fmt(odometer,0) : "—"} <small>${this._escape(odometerUnit)}</small></div>
              <div class="live-foot">${validOdometer ? "Lectura del vehículo" : "Odómetro no disponible"}</div>
            </div>
          </section>
          <div class="telemetry-freshness ${telemetryAgeMinutes === null ? "missing" : (freshnessParts.some(part => part.includes("no disponible") || part.includes("antiguo")) ? "stale" : "")}"><i></i>${this._escape(telemetryFreshness)}${telemetryAgeMinutes === null ? "" : " · hace " + this._fmt(telemetryAgeMinutes,0) + " min"}</div>` : ""}
          <div class="latest mode-${displayMode}">
            <div class="latest-heading">
              <div><div class="section-title">${current ? "Sesión en curso" : "Última carga"}</div><div class="chart-subtitle">${current ? "Datos en actualización" : (record.started_at ? this._date(record.started_at) : "Resumen de sesión")}</div></div>
              <span class="session-state">${current ? "EN CURSO" : (costStatus === "partial" ? "COSTE PARCIAL" : "RESUMEN")}</span>
            </div>
            <div class="session-energy"><strong>${energy === null ? "—" : this._fmt(energy,2)} <small>${this._escape(energyUnit)}</small></strong><span>ENERGÍA<br>ENTREGADA</span></div>
            <div class="rings">${this._socRing(socStart, "Batería inicial")}${this._socRing(socEnd, "Batería final")}</div>
            <div class="soc-progress" role="img" aria-label="Progreso de batería">${socStart !== null && socEnd !== null && socStart >= 0 && socStart <= 100 && socEnd >= socStart && socEnd <= 100 ? `<span style="width:${Math.max(0,Math.min(100,socEnd-socStart))}%"></span>` : ""}</div>
            <div class="metrics">
              <div class="metric"><strong>${increase === null ? "—" : "+" + this._fmt(increase,1) + " pp"}</strong><span>Aumento batería</span></div>
              <div class="metric"><strong>${this._duration(duration)}</strong><span>Duración</span></div>
              <div class="metric"><strong>${cost !== null ? this._fmt(cost,2) + " " + currency : (hasKnownCost ? this._fmt(knownCost,2) + " " + currency : "—")}</strong><span>${cost !== null ? "Coste total" : (hasKnownCost ? "Coste conocido · parcial" : "Coste no disponible")}</span></div>
              <div class="metric"><strong>${({ complete: "Completo", in_progress: "En curso", partial: "Parcial", unknown: "Sin datos" })[costStatus] || "Sin datos"}</strong><span>Estado del coste</span></div>
              <div class="metric"><strong>${!hasTariffData ? "Sin datos" : (tariffEstimated ? "Estimado" : "Precio aplicado")}</strong><span>Asignación de tarifa</span></div>
            </div>
            <div class="dates"><div class="date">Inicio<b>${start}</b></div><div class="date">Fin<b>${current && !record.ended_at ? "En curso" : end}</b></div></div>
            ${tariffBreakdown && Object.keys(tariffBreakdown).length ? `<div class="session-footnote">Desglose de tarifa: ${this._escape(Object.entries(tariffBreakdown).map(([period,value]) => period + " " + this._fmt(value,2) + " " + currency).join(" · "))}</div>` : ""}
            ${costStatus === "partial" ? '<div class="session-footnote">El importe mostrado solo incluye la parte del consumo con precio conocido; el coste final puede variar.</div>' : ""}
          </div>
          ${displayMode !== "compact" ? `<div class="charts">
            <section class="chart-card" aria-label="Energía por carga">
              <div class="chart-title">Energía por carga <span class="chart-subtitle">kWh · últimas ${chartRows.length}</span></div>
              ${chartRows.length ? `<div class="bars">${chartRows.map(item => {
                const value = Number(item.energy_kwh);
                const height = Math.max(4, value / maxEnergy * 72);
                const label = item.started_at ? new Intl.DateTimeFormat(this._hass?.locale?.language || "es-ES", { day:"2-digit", month:"short" }).format(new Date(item.started_at)) : "—";
                return `<div class="bar-wrap" title="${this._escape(this._fmt(value,2) + " kWh")}"><div class="bar" style="height:${height}px"></div><span class="bar-label">${this._escape(label)}</span></div>`;
              }).join("")}</div>` : '<div class="chart-empty">Aún no hay datos de energía suficientes</div>'}
              <div class="chart-legend">Consumo energético de cada sesión registrada</div>
            </section>
            <section class="chart-card" aria-label="Coste por carga">
              <div class="chart-title">Coste por carga <span class="chart-subtitle">${this._escape(currency)} · últimas ${costRows.length}</span></div>
              ${costRows.length ? `<div class="bars">${costRows.map(item => {
                const value = Number(item.cost ?? item.known_cost);
                const height = Math.max(4, value / maxCost * 72);
                const label = item.started_at ? new Intl.DateTimeFormat(this._hass?.locale?.language || "es-ES", { day:"2-digit", month:"short" }).format(new Date(item.started_at)) : "—";
                const partial = item.cost == null && item.known_cost != null;
                return `<div class="bar-wrap" title="${this._escape(this._fmt(value,2) + " " + currency + (partial ? " · parcial" : ""))}"><div class="bar cost" style="height:${height}px;opacity:${partial ? ".45" : ".82"}"></div><span class="bar-label">${this._escape(label)}</span></div>`;
              }).join("")}</div>` : '<div class="chart-empty">Sin costes calculables todavía</div>'}
              <div class="chart-legend">Los costes parciales se muestran atenuados</div>
            </section>
          </div>` : ""}
          ${displayMode !== "compact" ? `<div class="history-head"><h3>Histórico de cargas</h3><span class="count">${rows.length} registros</span></div>
          ${completedSessions.length ? `<section class="history-summary" aria-label="Resumen del histórico">
            <div class="history-summary-stats">
              <div><span>Energía total</span><strong>${this._fmt(totalHistoryEnergy,1)} kWh</strong></div>
              <div><span>Coste total</span><strong>${fullyPricedSessions.length ? this._fmt(totalHistoryCost,2) + " " + currency : "—"}</strong></div>
              <div><span>Coste medio</span><strong>${averageHistoryCost === null ? "—" : this._fmt(averageHistoryCost,3) + " " + currency + "/kWh"}</strong></div>
            </div>
            <div class="history-sparkline" aria-hidden="true">${historyBars.map(item => `<i style="height:${Math.max(4,Number(item.energy_kwh)/maxHistoryBar*56)}px"></i>`).join("")}</div>
          </section>` : ""}
          ${displayMode === "complete" && rows.length ? rows.map(item => {
            const itemEnergy = Number(item.energy_kwh);
            const itemCost = item.cost != null ? Number(item.cost) : (item.known_cost != null ? Number(item.known_cost) : null);
            const energyValid = item.energy_kwh != null && Number.isFinite(itemEnergy) && itemEnergy >= 0;
            const costValid = itemCost !== null && Number.isFinite(itemCost) && itemCost >= 0;
            const socValid = item.soc_start != null && item.soc_end != null && Number.isFinite(Number(item.soc_start)) && Number.isFinite(Number(item.soc_end));
            return `
            <div class="row">
              <div class="row-main"><div class="row-date">${this._date(item.started_at)}</div><div class="row-sub">${socValid ? this._fmt(item.soc_start,0)+"% → "+this._fmt(item.soc_end,0)+"%" : "Progreso de batería no disponible"}</div></div>
              <div class="row-stats"><div class="row-value">${energyValid ? this._fmt(itemEnergy,2)+" kWh" : "—"}<small>Energía</small></div><div class="row-value">${costValid ? this._fmt(itemCost,2)+" "+this._escape(item.currency || currency) : "—"}<small class="${item.cost_status === "partial" ? "cost-partial" : ""}">${item.cost_status === "partial" || (item.cost == null && item.known_cost != null) ? "Coste parcial" : (item.cost_status === "unknown" ? "Sin coste" : "Coste")}</small></div></div>
              <div class="row-energy"><span style="width:${energyValid && maxEnergy > 0 ? Math.max(0,Math.min(100,itemEnergy/maxEnergy*100)) : 0}%"></span></div>
            </div>`;
          }).join("") : (displayMode === "complete" ? '<div class="history-empty">Aún no hay cargas consolidadas.<br>Cuando finalice tu primera sesión, aparecerá aquí el resumen.</div>' : "")}
          ${diagnostic ? `<div class="diagnostic">${this._escape(diagnostic)}</div>` : ""}
        </div>` : ""}
      </ha-card>`;
    const customVehicleImage = typeof this.shadowRoot.querySelector === "function"
      ? this.shadowRoot.querySelector(".vehicle-image.custom") : null;
    if (customVehicleImage) customVehicleImage.addEventListener("error", () => {
      customVehicleImage.replaceWith(this._createFallbackVehicle(fallbackMarkup));
    }, { once: true });
  }

  _createFallbackVehicle(markup) {
    const template = document.createElement("template");
    template.innerHTML = markup;
    return template.content.firstElementChild;
  }

  _escape(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
      "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
    })[char]);
  }

  static getConfigElement() { return document.createElement("ev-charge-tracker-card-editor"); }
  static getStubConfig() { return { name: "Mi vehículo", entities: {} }; }
}

class EVChargeTrackerCardEditor extends HTMLElement {
  _validVehicleImage(value) {
    if (typeof value !== "string" || value.includes("..")) return false;
    if (/^\/local\/ev-charge-tracker\/(?:custom\/)?[A-Za-z0-9_-][A-Za-z0-9._-]*\.(png|webp)$/i.test(value)) return true;
    try {
      const url = new URL(value);
      const commonsImage = url.protocol === "https:" && url.hostname === "upload.wikimedia.org" &&
        /^\/wikipedia\/commons\/(?:thumb\/)?[A-Za-z0-9_./%()-]+\.(?:png|webp|jpe?g)(?:\/[^?#]+)?$/i.test(url.pathname);
      return commonsImage;
    } catch { return false; }
  }

  constructor() {
    super();
    this._config = {};
    this._hass = null;
    this._profiles = [];
    this._profilesLoaded = false;
    this._profileRequest = false;
    this._built = false;
    this._manualMode = false;
    this._galleryResults = [];
    this._gallerySequence = 0;
    this._galleryQueryEdited = false;
  }

  setConfig(config) {
    this._config = { ...(config || {}), entities: { ...(config?.entities || {}) } };
    this._syncControls();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._ensureDom();
    this.shadowRoot.querySelectorAll("ha-entity-picker").forEach(picker => {
      picker.hass = hass;
    });
    this._loadProfiles();
  }

  _ensureDom() {
    if (this._built) return;
    const fields = [
      ["status","Estado de carga"],["energy","Energía de la carga"],["cost","Coste de la carga"],
      ["soc_start","Batería al inicio"],["soc_end","Batería al final"],["soc_increase","Aumento de batería"],
      ["current_soc","Batería actual"],["odometer","Odómetro"],["range","Autonomía (sensor opcional)"],["plugged","Cable conectado"],
      ["duration","Duración"],["history","Histórico de cargas"],
    ];
    this.shadowRoot.innerHTML = `<style>
      :host{display:block;color:var(--primary-text-color)}
      .field{display:block;margin:15px 0} label{display:block;margin-bottom:7px;font-size:13px;font-weight:600}
      input,select{box-sizing:border-box;width:100%;padding:11px 12px;border:1px solid var(--divider-color);border-radius:12px;background:var(--card-background-color);color:var(--primary-text-color)}
      ha-entity-picker{display:block;width:100%}
      .hint{font-size:12px;color:var(--secondary-text-color);margin:7px 0 12px;line-height:1.45}
      .profile{margin:12px 0 18px;padding:15px;border:1px solid var(--divider-color);border-radius:16px;background:var(--secondary-background-color)}
      .vehicle-preview{display:flex;align-items:center;gap:12px;margin:12px 0;padding:12px;border-radius:14px;background:var(--card-background-color);min-height:62px}
      .preview-stage{position:relative;width:112px;height:58px;flex:0 0 112px}.preview-stage img{width:100%;height:100%;object-fit:contain}.vehicle-preview .preview-fallback{width:100%;height:100%;border-radius:12px;background:linear-gradient(145deg,var(--secondary-background-color),var(--divider-color));display:grid;place-items:center;font-size:25px}.preview-port{position:absolute;width:9px;height:9px;border:2px solid var(--primary-color);border-radius:50%;background:var(--card-background-color);transform:translate(-50%,-50%);pointer-events:none}
      .vehicle-preview strong{display:block;font-size:13px}.vehicle-preview small{display:block;margin-top:4px;color:var(--secondary-text-color);font-size:11px}
      .hidden{display:none}
      .gallery{margin:14px 0;padding:12px;border:1px solid var(--divider-color);border-radius:14px;background:var(--card-background-color)}
      .gallery-search{display:flex;gap:8px;align-items:center}.gallery-search input{min-width:0;flex:1}.gallery-search button{margin:0}
      .gallery-results{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin-top:10px}
      .gallery-item{display:block;width:100%;padding:7px!important;text-align:left;background:var(--secondary-background-color)!important;color:var(--primary-text-color)!important;border:1px solid var(--divider-color)!important}
      .gallery-item img{display:block;width:100%;height:92px;object-fit:contain;background:#f5f5f5;border-radius:8px}
      .gallery-item strong,.gallery-item small{display:block;margin-top:5px;font-size:11px;line-height:1.3}.gallery-item small{color:var(--secondary-text-color);font-size:10px}
      button{margin-top:10px;padding:9px 14px;border:0;border-radius:12px;background:var(--primary-color);color:var(--text-primary-color,var(--primary-background-color));font-weight:600;cursor:pointer}
      #entityFields{padding:4px 0 8px}
      #entityFields:not(.hidden){border-top:1px solid var(--divider-color);margin-top:12px}
      #max_history{max-width:140px}
      details{margin:12px 0;padding:12px;border:1px solid var(--divider-color);border-radius:12px}
      summary{cursor:pointer;font-size:13px;font-weight:650}
      details .field{margin:10px 0}
      #editorFeedback{min-height:18px;margin-top:8px}
      button:disabled{opacity:.55;cursor:wait}
      input:focus-visible,select:focus-visible,button:focus-visible,summary:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}
    </style><div>
      <div id="profileBox" class="profile hidden">
        <label for="profileSelect">Perfil de carga</label>
        <select id="profileSelect"></select>
        <div id="profileHint" class="hint"></div>
        <div id="vehiclePreview" class="vehicle-preview" aria-live="polite"></div>
        <details id="vehicleEditor"><summary>Personalizar identidad y puerto de carga</summary>
          <p class="hint">Selecciona un modelo del catálogo o añade una imagen personal. Usa siempre tres cuartos delantero, morro hacia la derecha, coche completo y fondo transparente. Las imágenes personales se guardan solo en este Home Assistant.</p>
          <label class="field">Modelo del vehículo<select id="visual_catalog"><option value="">Vehículo personalizado / no catalogado</option></select></label>
          <label class="field">Marca<input id="visual_brand" maxlength="40"></label>
          <label class="field">Modelo<input id="visual_model" maxlength="50"></label>
          <label class="field">Generación<input id="visual_generation" maxlength="40"></label>
          <label class="field">Año<input id="visual_year" maxlength="12"></label>
          <label class="field">Acabado<input id="visual_trim" maxlength="40"></label>
          <label class="field">Color<input id="visual_color" type="color"></label>
          <label class="field">Carrocería<select id="visual_body_style"><option value="suv">SUV</option><option value="sedan">Berlina</option><option value="hatchback">Compacto</option><option value="van">Furgoneta</option><option value="pickup">Pick-up</option></select></label>
          <label class="field">Añadir fotografía personal<input id="personalVehicleImage" type="file" accept="image/png,image/webp"></label><p class="hint">PNG/WebP transparentes de hasta 8 MB. Se normalizan a 1200 × 675 px y se guardan localmente; no se envían a servicios externos.</p><input id="visual_image" type="hidden">
          <label class="field">Puerto horizontal (0-100)<input id="visual_port_x" type="number" min="0" max="100"></label>
          <label class="field">Puerto vertical (0-100)<input id="visual_port_y" type="number" min="0" max="100"></label>
        </details>
        <div id="editorFeedback" class="hint" role="status" aria-live="polite"></div>
        <button id="refreshProfiles" type="button">Actualizar perfiles</button>
        <button id="manualToggle" type="button">Editar entidades manualmente</button>
      </div>
      <label class="field">Nombre visible<input id="name" placeholder="Mi vehículo"></label>
      <label class="field">Densidad de información<select id="display_mode"><option value="compact">Compacto · esencial</option><option value="balanced">Equilibrado · gráficos y resumen</option><option value="complete">Completo · todo el histórico</option></select></label>\n      <label class="field">Apariencia<select id="theme_mode"><option value="auto">Automática · seguir Home Assistant</option><option value="light">Clara</option><option value="dark">Oscura</option></select></label>
      <div id="entityFields" class="hidden">
        ${fields.map(([key,label]) => `<label class="field">${label}<ha-entity-picker data-key="${key}" allow-custom-entity></ha-entity-picker></label>`).join("")}
      </div>
      <label class="field">Máximo de cargas históricas<input id="max_history" type="number" min="1" max="50"></label>
    </div>`;
    this.shadowRoot.getElementById("name").addEventListener("change", () => this._updateConfig());
    this.shadowRoot.getElementById("max_history").addEventListener("change", () => this._updateConfig());
    this.shadowRoot.getElementById("display_mode").addEventListener("change", () => this._updateConfig());
    this.shadowRoot.getElementById("theme_mode").addEventListener("change", () => this._updateConfig());
    ["brand","model","generation","year","trim","color","body_style","image","port_x","port_y"].forEach(key => {
      const field = this.shadowRoot.getElementById("visual_" + key);
      if (field) field.addEventListener(key === "color" || key === "body_style" ? "change" : "input", () => this._updateConfig());
    });
    this.shadowRoot.getElementById("profileSelect").addEventListener("change", event => {
      const selected = this._profiles.find(profile => profile.entry_id === event.target.value);
      if (selected) this._applyProfile(selected);
    });
    this.shadowRoot.getElementById("refreshProfiles").addEventListener("click", () => this._loadProfiles(true));
    this.shadowRoot.getElementById("visual_catalog").addEventListener("change", event => this._selectCatalogVehicle(event.target.value));
    this.shadowRoot.getElementById("personalVehicleImage").addEventListener("change", event => this._uploadPersonalVehicleImage(event.target.files?.[0]));
    this.shadowRoot.getElementById("manualToggle").addEventListener("click", () => {
      this._manualMode = !this._manualMode;
      this._syncControls();
    });
    this.shadowRoot.querySelectorAll("ha-entity-picker").forEach(picker => {
      picker.addEventListener("value-changed", event => {
        if (event.detail?.value !== picker.value) return;
        this._updateConfig(picker.dataset.key, event.detail.value);
      });
    });
    this._built = true;
    this._syncControls();
  }

  _selectCatalogVehicle(id) {
    if (id === "__personal__") {
      const picker = this.shadowRoot.getElementById("personalVehicleImage");
      if (picker) picker.click();
      const visual = this._config.vehicle_visual || {};
      const selected = VEHICLE_CATALOG.find(item => item.brand.toLowerCase() === String(visual.visual_brand || "").toLowerCase() && item.model.toLowerCase() === String(visual.visual_model || "").toLowerCase());
      this.shadowRoot.getElementById("visual_catalog").value = selected?.id || "";
      return;
    }
    const item = VEHICLE_CATALOG.find(vehicle => vehicle.id === id);
    if (!item) return;
    const next = { ...this._config, vehicle_visual: { ...(this._config.vehicle_visual || {}) } };
    Object.assign(next.vehicle_visual, { visual_brand: item.brand, visual_model: item.model, visual_body_style: item.body, visual_image: item.image || "" });
    for (const key of ["visual_image_credit","visual_image_license","visual_image_license_url","visual_image_page","visual_image_source"]) delete next.vehicle_visual[key];
    next.vehicle_visual_override = true;
    this._config = next;
    this._syncControls();
    this._updateConfig();
    const feedback = this.shadowRoot.getElementById("editorFeedback");
    if (feedback) feedback.textContent = item.image
      ? "Modelo seleccionado. Se ha aplicado su imagen predeterminada."
      : "Modelo seleccionado. Todavía no hay un render del catálogo con licencia y formato verificados; puedes añadir tu imagen personal.";
  }

  async _uploadPersonalVehicleImage(file) {
    const feedback = this.shadowRoot.getElementById("editorFeedback");
    const input = this.shadowRoot.getElementById("personalVehicleImage");
    if (!file) return;
    if (!["image/png","image/webp"].includes(file.type) || file.size > 8 * 1024 * 1024) {
      if (feedback) feedback.textContent = "Selecciona un PNG o WebP de hasta 8 MB.";
      if (input) input.value = "";
      return;
    }
    try {
      const bitmap = await createImageBitmap(file);
      if (bitmap.width > 6000 || bitmap.height > 6000 || bitmap.width * bitmap.height > 25000000) {
        bitmap.close?.();
        throw new Error("La imagen supera las dimensiones máximas admitidas.");
      }
      const source = document.createElement("canvas");
      source.width = bitmap.width;
      source.height = bitmap.height;
      const sourceContext = source.getContext("2d", { willReadFrequently: true });
      sourceContext.drawImage(bitmap, 0, 0);
      bitmap.close?.();
      const pixels = sourceContext.getImageData(0, 0, source.width, source.height).data;
      let transparent = 0, opaque = 0, samples = 0;
      let minX = source.width, minY = source.height, maxX = -1, maxY = -1;
      const stride = Math.max(4, Math.floor((source.width * source.height) / 200000) * 4);
      for (let i = 3; i < pixels.length; i += stride) {
        samples++;
        const alpha = pixels[i];
        if (alpha < 24) transparent++;
        if (alpha > 24) {
          opaque++;
          const pixel = (i - 3) / 4;
          const x = pixel % source.width, y = Math.floor(pixel / source.width);
          minX = Math.min(minX, x); minY = Math.min(minY, y);
          maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
        }
      }
      if (transparent / Math.max(1,samples) < 0.12 || opaque / Math.max(1,samples) < 0.08 || maxX < minX || maxY < minY) {
        throw new Error("La imagen debe tener un vehículo visible y una zona de fondo realmente transparente.");
      }
      const cropWidth = maxX - minX + 1, cropHeight = maxY - minY + 1;
      const canvas = document.createElement("canvas");
      canvas.width = 1200;
      canvas.height = 675;
      const context = canvas.getContext("2d");
      const scale = Math.min(1080 / cropWidth, 595 / cropHeight);
      const width = cropWidth * scale, height = cropHeight * scale;
      context.drawImage(source, minX, minY, cropWidth, cropHeight, (1200 - width) / 2, (675 - height) / 2, width, height);
      const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
      if (!blob) throw new Error("No se pudo preparar la imagen.");
      if (blob.size > 8 * 1024 * 1024) throw new Error("La imagen normalizada supera el límite de 8 MB. Usa un archivo de menor resolución.");
      if (feedback) feedback.textContent = "Normalizando imagen y guardándola en Home Assistant…";
      const token = this._hass?.auth?.data?.access_token;
      if (!token) throw new Error("No se ha podido obtener la sesión autenticada de Home Assistant.");
      const uploadUrl = typeof this._hass.hassUrl === "function"
        ? this._hass.hassUrl("/api/ev_charge_tracker/vehicle-image")
        : "/api/ev_charge_tracker/vehicle-image";
      const response = await fetch(uploadUrl, {
        method: "POST",
        headers: { Authorization: "Bearer " + token, "Content-Type": "image/png" },
        body: blob,
      });
      if (!response.ok) throw new Error((await response.text()) || ("HTTP " + response.status));
      const result = await response.json();
      if (!/^\/local\/ev-charge-tracker\/custom\/[a-f0-9]{64}\.png$/.test(result.path || "")) {
        throw new Error("Home Assistant devolvió una ruta de imagen no válida.");
      }
      const imageField = this.shadowRoot.getElementById("visual_image");
      if (imageField) imageField.value = result.path;
      const next = { ...this._config, vehicle_visual: { ...(this._config.vehicle_visual || {}), visual_image: result.path } };
      for (const key of ["visual_image_credit","visual_image_license","visual_image_license_url","visual_image_page","visual_image_source"]) delete next.vehicle_visual[key];
      next.vehicle_visual_override = true;
      this._config = next;
      this._updateConfig();
      if (feedback) feedback.textContent = "Imagen personal guardada en este Home Assistant. Pulsa Guardar en el editor del panel.";
    } catch (error) {
      if (feedback) feedback.textContent = error?.message || "No se pudo guardar la imagen.";
    } finally {
      if (input) input.value = "";
    }
  }

  async _searchVehicleGallery() {
    const query = (this.shadowRoot?.getElementById("galleryQuery")?.value || "").trim();
    const status = this.shadowRoot?.getElementById("galleryStatus");
    const results = this.shadowRoot?.getElementById("galleryResults");
    if (!query) { if (status) status.textContent = "Escribe una marca y un modelo."; return; }
    const sequence = ++this._gallerySequence;
    if (status) status.textContent = "Buscando imágenes y comprobando licencias…";
    if (results) results.innerHTML = "";
    const params = new URLSearchParams({action:"query",format:"json",origin:"*",generator:"search",gsrsearch:"filetype:bitmap "+query,gsrnamespace:"6",gsrlimit:"24",prop:"imageinfo",iiprop:"url|extmetadata",iiurlwidth:"900",iiextmetadatalanguage:"es"});
    try {
      const response = await fetch("https://commons.wikimedia.org/w/api.php?"+params.toString(),{headers:{Accept:"application/json"}});
      if (!response.ok) throw new Error("HTTP "+response.status);
      const data = await response.json();
      if (sequence !== this._gallerySequence) return;
      const clean = value => String(value||"").replace(/<[^>]*>/g," ").replace(/&amp;/g,"&").replace(/&#39;/g,"'").replace(/&quot;/g,'"').replace(/\s+/g," ").trim();
      const allowed = /^(CC0(?: 1\.0)?|Public domain|CC BY 4\.0|CC BY-SA 4\.0|CC BY 3\.0|CC BY-SA 3\.0|CC BY 2\.0|CC BY-SA 2\.0)$/i;
      this._galleryResults = Object.values(data?.query?.pages||{}).map(page => {
        const info=page.imageinfo?.[0], meta=info?.extmetadata||{}, license=clean(meta.LicenseShortName?.value), image=info?.thumburl||info?.url;
        if (!image || !/^https:\/\/upload\.wikimedia\.org\/wikipedia\/commons\//i.test(image) || !allowed.test(license)) return null;
        return {title:page.title||"Imagen",image,page:info.descriptionurl||"",author:clean(meta.Artist?.value||meta.Credit?.value||"Autor no indicado"),license,licenseUrl:clean(meta.LicenseUrl?.value||"")};
      }).filter(Boolean).slice(0,12);
      if (!this._galleryResults.length) { if(status) status.textContent="No hay resultados con licencia libre reconocida. Prueba otra búsqueda."; return; }
      if(status) status.textContent=this._galleryResults.length+" imágenes libres verificadas. Selecciona una.";
      results.innerHTML=this._galleryResults.map((item,index)=>'<button type="button" class="gallery-item" data-gallery-index="'+index+'"><img loading="lazy" src="'+this._esc(item.image)+'" alt="'+this._esc(item.title)+'"><strong>'+this._esc(item.title.replace(/^File:/,""))+'</strong><small>'+this._esc(item.license)+' · '+this._esc(item.author)+'</small></button>').join("");
    } catch(error) { if(sequence===this._gallerySequence && status) status.textContent="No se pudo consultar Wikimedia Commons. Comprueba la conexión e inténtalo de nuevo."; }
  }

  _selectGalleryImage(item) {
    if(!item) return;
    const next={...this._config,vehicle_visual:{...(this._config.vehicle_visual||{})}};
    Object.assign(next.vehicle_visual,{visual_image:item.image,visual_image_credit:item.author,visual_image_license:item.license,visual_image_license_url:item.licenseUrl,visual_image_page:item.page,visual_image_source:"Wikimedia Commons"});
    next.vehicle_visual_override = true;
    this._config=next;
    const input=this.shadowRoot.getElementById("visual_image"); if(input) input.value=item.image;
    this._updateConfig();
    const status=this.shadowRoot.getElementById("galleryStatus"); if(status) status.textContent="Imagen seleccionada con autoría y licencia. Guarda los cambios de la tarjeta.";
  }

  async _loadProfiles(force = false) {
    if (!this._hass || (!force && this._profilesLoaded) || this._profileRequest || typeof this._hass.callWS !== "function") return;
    this._profileRequest = true;
    const refreshButton = this.shadowRoot?.getElementById("refreshProfiles");
    if (refreshButton) { refreshButton.disabled = true; refreshButton.textContent = "Actualizando…"; }
    try {
      const result = await this._hass.callWS({ type: "ev_charge_tracker/profiles" });
      this._profiles = Array.isArray(result?.profiles) ? result.profiles : [];
      this._profilesLoaded = true;
      const selectedId = this._config.profile_entry_id;
      if (selectedId) {
        const selected = this._profiles.find(profile => profile.entry_id === selectedId);
        if (selected && !this._config.profile_manual_override) this._applyProfile(selected, false);
      } else if (this._profiles.length === 1) {
        this._applyProfile(this._profiles[0], false);
      } else if (this._profiles.length > 1) {
        this._manualMode = false;
      } else {
        this._manualMode = true;
      }
      this._syncControls();
      const refresh = this.shadowRoot?.getElementById("refreshProfiles");
      if (refresh) refresh.textContent = "Perfiles actualizados ✓";
      const feedback = this.shadowRoot?.getElementById("editorFeedback");
      if (feedback) feedback.textContent = "Perfiles cargados correctamente."; 
    } catch (error) {
      // Keep manual configuration available if the backend profile API is unavailable.
      this._profilesLoaded = true;
      this._manualMode = true;
      this._syncControls();
      const refresh = this.shadowRoot?.getElementById("refreshProfiles");
      if (refresh) refresh.textContent = "Error al actualizar · Reintentar";
      const feedback = this.shadowRoot?.getElementById("editorFeedback");
      if (feedback) feedback.textContent = "No se pudieron cargar los perfiles. Puedes reintentar o configurar entidades manualmente.";
    } finally {
      this._profileRequest = false;
      const refresh = this.shadowRoot?.getElementById("refreshProfiles");
      if (refresh) refresh.disabled = false;
    }
  }

  _profileVisualKey(profile) {
    const visual = profile?.vehicle_visual || {};
    const identity = [visual.visual_brand, visual.visual_model].filter(Boolean).join(" ") ||
      profile?.vehicle_name || profile?.entry_id || "manual";
    return String(identity).normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "manual";
  }

  _applyProfile(profile, emit = true) {
    const visualKey = this._profileVisualKey(profile);
    const savedVisual = this._config.vehicle_visuals?.[visualKey];
    const isSameProfile = this._config.profile_entry_id === profile.entry_id;
    const legacyVisual = isSameProfile && this._config.vehicle_visual_override
      ? this._config.vehicle_visual : null;
    const vehicleVisual = savedVisual || legacyVisual || profile.vehicle_visual || {};
    const next = {
      ...this._config,
      name: profile.vehicle_name || this._config.name || "ChargeTrack",
      profile_entry_id: profile.entry_id,
      entities: { ...(this._config.entities || {}), ...(profile.entities || {}) },
      vehicle_visual: { ...vehicleVisual },
      vehicle_visual_override: Boolean(savedVisual || legacyVisual),
    };
    for (const key of Object.keys(next.entities)) {
      if (!profile.entities?.[key]) delete next.entities[key];
    }
    this._config = next;
    this._manualMode = false;
    this._galleryQueryEdited = false;
    this._syncControls();
    if (emit) this._fireConfigChanged();
  }

  _syncControls() {
    if (!this.shadowRoot || !this._built) return;
    const name = this.shadowRoot.getElementById("name");
    const maxHistory = this.shadowRoot.getElementById("max_history");
    const displayMode = this.shadowRoot.getElementById("display_mode");
    const themeMode = this.shadowRoot.getElementById("theme_mode");
    if (name && name !== this.shadowRoot.activeElement) name.value = this._config.name || "";
    if (maxHistory && maxHistory !== this.shadowRoot.activeElement) maxHistory.value = this._config.max_history || 8;
    if (displayMode && displayMode !== this.shadowRoot.activeElement) displayMode.value = this._config.display_mode || "balanced";
    if (themeMode && themeMode !== this.shadowRoot.activeElement) themeMode.value = this._config.theme_mode || "auto";
    const visual = this._config.vehicle_visual || {};
    const profile = this._profiles.find(item => item.entry_id === this._config.profile_entry_id);
    const catalog = this.shadowRoot.getElementById("visual_catalog");
    if (catalog && catalog.options.length !== VEHICLE_CATALOG.length + 2) {
      catalog.innerHTML = '<option value="">Vehículo personalizado / no catalogado</option>' + VEHICLE_CATALOG.map(item =>
        '<option value="' + this._esc(item.id) + '">' + this._esc(item.label) + (item.image ? '' : ' · imagen por añadir') + '</option>'
      ).join("") + '<option value="__personal__">➕ Añadir una foto personal</option>';
    }
    const matchingCatalog = VEHICLE_CATALOG.find(item =>
      item.brand.toLowerCase() === String(visual.visual_brand || "").toLowerCase() &&
      item.model.toLowerCase() === String(visual.visual_model || "").toLowerCase()
    );
    if (catalog && this.shadowRoot.activeElement !== catalog) catalog.value = matchingCatalog?.id || "";
    ["brand","model","generation","year","trim","color","body_style","image","port_x","port_y"].forEach(key => {
      const field = this.shadowRoot.getElementById("visual_" + key);
      if (field && field !== this.shadowRoot.activeElement) {
        const activeProfile = this._profiles.find(item => item.entry_id === this._config.profile_entry_id);
      const identityText = [visual.visual_brand, visual.visual_model, activeProfile?.vehicle_name, this._config.name].filter(Boolean).join(" ");
      const isLeapmotorC10 = /c10/i.test(identityText) && (!visual.visual_brand || /leapmotor/i.test(visual.visual_brand) || /leapmotor/i.test(identityText));
        const defaults = { color: "#71869A", body_style: "suv", port_x: isLeapmotorC10 ? 83 : 67, port_y: isLeapmotorC10 ? 57 : 44 };
        field.value = visual["visual_" + key] ?? (defaults[key] ?? "");
      }
    });

    const profileBox = this.shadowRoot.getElementById("profileBox");
    const profileSelect = this.shadowRoot.getElementById("profileSelect");
    const profileHint = this.shadowRoot.getElementById("profileHint");
    const hasProfiles = this._profiles.length > 0;
    profileBox.classList.toggle("hidden", !hasProfiles);
    if (hasProfiles) {
      const selectedId = this._config.profile_entry_id || (this._profiles.length === 1 ? this._profiles[0].entry_id : "");
      if (profileSelect.options.length !== this._profiles.length) {
        profileSelect.innerHTML = `<option value="">Selecciona un perfil…</option>` + this._profiles.map(profile =>
          `<option value="${this._esc(profile.entry_id)}">${this._esc(profile.vehicle_name)} · ${this._esc(profile.charger_name)}</option>`
        ).join("");
      }
      if (selectedId && profileSelect.value !== selectedId) profileSelect.value = selectedId;
      profileSelect.classList.toggle("hidden", this._profiles.length === 1);
      const activeProfile = this._profiles.find(profile => profile.entry_id === selectedId);
      profileHint.textContent = activeProfile
        ? "Perfil activo: " + activeProfile.vehicle_name + " · " + activeProfile.charger_name
        : "Selecciona el vehículo y cargador que utilizará esta tarjeta.";
    }
    const preview = this.shadowRoot.getElementById("vehiclePreview");
    if (preview) {
      const visual = this._config.vehicle_visual || {};
      const label = [visual.visual_brand, visual.visual_model].filter(Boolean).join(" ") || this._config.name || "Vehículo";
      const details = [visual.visual_generation, visual.visual_year, visual.visual_trim].filter(Boolean).join(" · ");
      const activeProfile = this._profiles.find(item => item.entry_id === this._config.profile_entry_id);
      const identityText = [visual.visual_brand, visual.visual_model, activeProfile?.vehicle_name, this._config.name].filter(Boolean).join(" ");
      const isLeapmotorC10 = /c10/i.test(identityText) && (!visual.visual_brand || /leapmotor/i.test(visual.visual_brand) || /leapmotor/i.test(identityText));
      const image = this._validVehicleImage(visual.visual_image) ? visual.visual_image : (isLeapmotorC10 ? DEFAULT_C10_IMAGE_URL : "");
      const defaultPortX = isLeapmotorC10 ? 83 : 67;
      const defaultPortY = isLeapmotorC10 ? 57 : 44;
      const rawPortX = Number(visual.visual_port_x ?? defaultPortX);
      const rawPortY = Number(visual.visual_port_y ?? defaultPortY);
      const portX = Number.isFinite(rawPortX) ? Math.min(100, Math.max(0, rawPortX)) : defaultPortX;
      const portY = Number.isFinite(rawPortY) ? Math.min(100, Math.max(0, rawPortY)) : defaultPortY;
      const imageOrFallback = image
        ? '<img src="' + this._esc(image) + '" alt="' + this._esc(label) + '">'
        : '<div class="preview-fallback" role="img" aria-label="Imagen del vehículo no disponible">Imagen del vehículo no disponible</div>';
      preview.innerHTML = '<div class="preview-stage">' + imageOrFallback +
        '<i class="preview-port" style="left:' + portX + '%;top:' + portY + '%"></i></div>' +
        '<div><strong>' + this._esc(label) + '</strong><small>' + this._esc(details || "Vista previa de identidad del vehículo") + '</small></div>';
      if (visual.visual_image_credit && visual.visual_image_license) {
        const credit = document.createElement("small");
        credit.textContent = "Imagen: " + visual.visual_image_credit + " · " + visual.visual_image_license;
        preview.lastElementChild.appendChild(credit);
      }
      const imageNode = preview.querySelector("img");
      if (imageNode) imageNode.addEventListener("error", () => {
        const fallback = document.createElement("div");
        fallback.className = "preview-fallback";
        fallback.textContent = "Imagen no disponible";
        imageNode.replaceWith(fallback);
      }, { once: true });
    }
    const entityFields = this.shadowRoot.getElementById("entityFields");
    entityFields.classList.toggle("hidden", !this._manualMode);
    this.shadowRoot.getElementById("manualToggle").textContent =
      this._manualMode ? "Ocultar edición manual" : "Editar entidades manualmente";
    this.shadowRoot.querySelectorAll("ha-entity-picker").forEach(picker => {
      picker.hass = this._hass;
      const value = this._config.entities?.[picker.dataset.key] || "";
      if (picker.value !== value) picker.value = value;
    });
  }

  _updateConfig(changedKey, changedValue) {
    const name = this.shadowRoot.getElementById("name").value.trim() || "ChargeTrack";
    const maxHistory = Math.min(50, Math.max(1, Number(this.shadowRoot.getElementById("max_history").value || 8)));
    const displayMode = this.shadowRoot.getElementById("display_mode").value || "balanced";
    const themeMode = this.shadowRoot.getElementById("theme_mode").value || "auto";
    const previousImage = this._config.vehicle_visual?.visual_image || "";
    const next = { ...this._config, name, max_history: maxHistory, display_mode: displayMode, theme_mode: themeMode, entities: { ...(this._config.entities || {}) }, vehicle_visual: { ...(this._config.vehicle_visual || {}) } };
    let imagePathError = false;
    ["brand","model","generation","year","trim","color","body_style","image","port_x","port_y"].forEach(key => {
      const field = this.shadowRoot.getElementById("visual_" + key);
      if (!field) return;
      const configKey = "visual_" + key;
      let value = field.value.trim();
      if (key === "image") {
        const validPath = new RegExp("^/local/ev-charge-tracker/(?:custom/)?[A-Za-z0-9_-][A-Za-z0-9._-]*[.](png|webp)$", "i").test(value) && !value.includes("..");
        const validCommons = this._validVehicleImage(value);
        if (value && !validPath && !validCommons) { field.setCustomValidity("Usa una ruta local o una imagen seleccionada de Wikimedia Commons."); imagePathError = true; value = ""; }
        else field.setCustomValidity("");
      }
      if (key === "color" && !new RegExp("^#[0-9a-f]{6}$", "i").test(value)) value = "#71869A";
      if (key === "port_x" || key === "port_y") {
        const number = Number(value);
        value = String(Number.isFinite(number) ? Math.min(100, Math.max(0, number)) : (key === "port_x" ? 67 : 44));
      }
      if (value) next.vehicle_visual[configKey] = value; else delete next.vehicle_visual[configKey];
    });
    if ((next.vehicle_visual.visual_image || "") !== previousImage) {
      delete next.vehicle_visual.visual_image_credit;
      delete next.vehicle_visual.visual_image_license;
      delete next.vehicle_visual.visual_image_license_url;
      delete next.vehicle_visual.visual_image_page;
      delete next.vehicle_visual.visual_image_source;
    }
    if (this.shadowRoot.activeElement?.id?.startsWith("visual_")) next.vehicle_visual_override = true;
    const activeProfile = this._profiles.find(profile => profile.entry_id === next.profile_entry_id);
    const visualKey = activeProfile ? this._profileVisualKey(activeProfile) : "manual";
    next.vehicle_visuals = { ...(next.vehicle_visuals || {}), [visualKey]: { ...next.vehicle_visual } };
    if (changedKey) {
      if (changedValue) next.entities[changedKey] = changedValue;
      else delete next.entities[changedKey];
      // A manual override is intentional; do not silently reapply profile defaults.
      next.profile_manual_override = true;
    }
    this._config = next;
    const feedback = this.shadowRoot.getElementById("editorFeedback");
    if (feedback) feedback.textContent = imagePathError
      ? "La imagen no es válida. Usa una ruta local PNG/WebP o selecciona una imagen de la galería gratuita."
      : "Cambios enviados a Lovelace, pero aún pendientes de guardar. Pulsa Guardar en el editor del panel. Home Assistant no ofrece a esta tarjeta una confirmación fiable de que el guardado haya terminado.";
    this._syncControls();
    this._fireConfigChanged();
  }

  _fireConfigChanged() {
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config: this._config }, bubbles: true, composed: true,
    }));
  }

  _esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({
      "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
    }[c]));
  }
}
customElements.define("ev-charge-tracker-card", EVChargeTrackerCard);
customElements.define("ev-charge-tracker-card-editor", EVChargeTrackerCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "ev-charge-tracker-card",
  name: "ChargeTrack",
  description: "Resumen de carga, batería, coste e histórico de vehículo eléctrico.",
  preview: true,
  version: CARD_VERSION,
});
