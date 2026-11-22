/* EV Charge Tracker Lovelace card
 * Copyright (c) EV Charge Tracker contributors. MIT.
 */
const CARD_VERSION = "0.3.0";

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
  }

  getCardSize() { return 5; }

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
    const duration = this._number(e.duration);
    // Live vehicle telemetry is deliberately separate from session SOC start/end.
    const liveSoc = this._number(e.soc_current);
    const odometer = this._number(e.odometer);
    const odometerUnit = this._attr(e.odometer, "unit_of_measurement", "km");
    const history = this._attr(e.history, "sessions", []);
    const current = this._attr(e.history, "current_session", null);
    const latest = this._attr(e.history, "latest_session", null);
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
    const title = this.config.name || this.config.vehicle || "EV Charge Tracker";
    const start = this._date(record.started_at);
    const end = this._date(record.ended_at || record.completed_at);
    const maxHistory = Math.min(50, Math.max(1, Math.trunc(Number(this.config.max_history) || 8)));
    const rows = Array.isArray(history) ? history.slice(0, maxHistory) : [];
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
        .wrap { padding:20px; background:var(--ha-card-background,var(--card-background-color)); }
        .top { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
        .eyebrow { color:var(--secondary-text-color); font-size:11px; font-weight:700; letter-spacing:.13em; text-transform:uppercase; }
        h2 { margin:5px 0 0; font-size:21px; font-weight:650; letter-spacing:-.03em; }
        .status { display:inline-flex; align-items:center; gap:7px; border-radius:30px; padding:7px 11px; background:var(--secondary-background-color); color:var(--secondary-text-color); font-size:12px; white-space:nowrap; }
        .dot { width:7px; height:7px; border-radius:50%; background:var(--success-color,#43a66b); }
        .status.active .dot { background:var(--state-active-color,var(--primary-color)); box-shadow:0 0 0 4px color-mix(in srgb,var(--primary-color) 15%,transparent); }
        .status.warn .dot { background:var(--warning-color,#d69b32); }
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
        .vehicle-live { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:9px; margin-top:12px; }
        .live-item { min-width:0; padding:12px 14px; border-radius:14px; background:var(--card-background-color); }
        .live-item strong { display:block; font-size:20px; font-weight:680; letter-spacing:-.04em; }
        .live-item span { display:block; margin-top:4px; color:var(--secondary-text-color); font-size:11px; }
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
        @media(max-width:520px) { .charts{grid-template-columns:1fr;gap:9px}.chart-card{padding:12px}.bars{height:78px} }
        @media(max-width:420px) { .wrap{padding:15px}.ring{width:72px;height:72px}.ring span{font-size:19px}.metric{padding:10px 8px}.metric strong{font-size:17px}.row{grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr) minmax(0,.8fr)} }
      </style>
      <ha-card>
        <div class="wrap">
          <div class="top">
            <div><div class="eyebrow">Cargas · Última carga</div><h2>${this._escape(title)}</h2></div>
            <div class="status ${charging ? "active" : (statusWarning ? "warn" : "")}">
              <i class="dot"></i>${this._escape(statusLabels[status] || status)}
            </div>
          </div>
          <div class="latest">
            <div class="section-title">${current ? "Carga actual" : "Resumen de la última carga"}</div>
            <div class="rings">
              ${this._socRing(socStart, "Batería inicial")}
              ${this._socRing(socEnd, "Batería final")}
            </div>
            <div class="metrics">
              <div class="metric"><strong>${increase === null ? "—" : "+" + this._fmt(increase,1) + " pp"}</strong><span>Aumento batería</span></div>
              <div class="metric"><strong>${this._duration(duration)}</strong><span>Duración</span></div>
              <div class="metric"><strong>${energy === null ? "—" : this._fmt(energy,2) + " " + energyUnit}</strong><span>Energía</span></div>
              <div class="metric"><strong>${cost !== null ? this._fmt(cost,2) + " " + currency : (hasKnownCost ? this._fmt(knownCost,2) + " " + currency : "—")}</strong><span>${cost !== null ? "Coste total" : (hasKnownCost ? "Coste conocido · parcial" : "Coste")}</span></div>
              <div class="metric"><strong>${({ complete: "Completo", in_progress: "En curso", partial: "Parcial", unknown: "Sin datos" })[costStatus] || "Sin datos"}</strong><span>Estado del coste</span></div>
              <div class="metric"><strong>${!hasTariffData ? "Sin datos" : (tariffEstimated ? "Estimado" : "Precio aplicado")}</strong><span>Cálculo de tarifa</span></div>
            </div>
            <div class="dates">
              <div class="date">Inicio<b>${start}</b></div>
              <div class="date">Fin<b>${current && !record.ended_at ? "En curso" : end}</b></div>
            </div>
            ${(e.soc_current || e.odometer) ? `<div class="vehicle-live" aria-label="Datos actuales del vehículo">
              ${e.soc_current ? `<div class="live-item"><strong>${liveSoc === null || liveSoc < 0 || liveSoc > 100 ? "—" : this._fmt(liveSoc,0) + "%"}</strong><span>Batería actual</span></div>` : ""}
              ${e.odometer ? `<div class="live-item"><strong>${odometer === null ? "—" : this._fmt(odometer,0) + " " + this._escape(odometerUnit)}</strong><span>Kilometraje actual</span></div>` : ""}
            </div>` : ""}
          </div>
          <div class="charts">
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
          </div>
          <div class="history-head"><h3>Histórico de cargas</h3><span class="count">${rows.length} registros</span></div>
          ${rows.length ? rows.map(item => `
            <div class="row">
              <div><div class="row-date">${this._date(item.started_at)}</div><div class="row-sub">${item.soc_start == null ? "—" : this._fmt(item.soc_start,0)+"%"} → ${item.soc_end == null ? "—" : this._fmt(item.soc_end,0)+"%"}</div></div>
              <div class="row-value">${item.energy_kwh == null ? "—" : this._fmt(item.energy_kwh,2)+" kWh"}<small>Energía</small></div>
              <div class="row-value">${item.cost != null ? this._fmt(item.cost,2)+" "+this._escape(item.currency || currency) : (item.known_cost != null ? this._fmt(item.known_cost,2)+" "+this._escape(item.currency || currency) : "—")}<small>${item.cost_status === "partial" ? "Coste parcial" : (item.cost_status === "unknown" ? "Sin coste" : "Coste")}</small></div>
            </div>`).join("") : '<div class="empty">Todavía no hay cargas consolidadas. Cuando termine la primera sesión aparecerá aquí.</div>'}
          ${diagnostic ? `<div class="diagnostic">${this._escape(diagnostic)}</div>` : ""}
        </div>
      </ha-card>`;
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
  constructor() {
    super();
    this._config = {};
    this._hass = null;
    this._profiles = [];
    this._profilesLoaded = false;
    this._profileRequest = false;
    this._built = false;
    this._manualMode = false;
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
      ["duration","Duración"],["history","Histórico de cargas"],
    ];
    this.shadowRoot.innerHTML = `<style>
      :host{display:block;color:var(--primary-text-color)}
      .field{display:block;margin:15px 0} label{display:block;margin-bottom:7px;font-size:13px;font-weight:600}
      input,select{box-sizing:border-box;width:100%;padding:11px 12px;border:1px solid var(--divider-color);border-radius:12px;background:var(--card-background-color);color:var(--primary-text-color)}
      ha-entity-picker{display:block;width:100%}
      .hint{font-size:12px;color:var(--secondary-text-color);margin:7px 0 12px;line-height:1.45}
      .profile{margin:12px 0 18px;padding:15px;border:1px solid var(--divider-color);border-radius:16px;background:var(--secondary-background-color)}
      .hidden{display:none}
      button{margin-top:10px;padding:9px 14px;border:0;border-radius:12px;background:var(--primary-color);color:var(--text-primary-color,var(--primary-background-color));font-weight:600;cursor:pointer}
      #entityFields{padding:4px 0 8px}
      #entityFields:not(.hidden){border-top:1px solid var(--divider-color);margin-top:12px}
      #max_history{max-width:140px}
    </style><div>
      <div id="profileBox" class="profile hidden">
        <label for="profileSelect">Perfil de carga</label>
        <select id="profileSelect"></select>
        <div id="profileHint" class="hint"></div>
        <button id="manualToggle" type="button">Editar entidades manualmente</button>
      </div>
      <label class="field">Nombre visible<input id="name" placeholder="Mi vehículo"></label>
      <div id="entityFields" class="hidden">
        ${fields.map(([key,label]) => `<label class="field">${label}<ha-entity-picker data-key="${key}" allow-custom-entity></ha-entity-picker></label>`).join("")}
      </div>
      <label class="field">Máximo de cargas históricas<input id="max_history" type="number" min="1" max="50"></label>
    </div>`;
    this.shadowRoot.getElementById("name").addEventListener("change", () => this._updateConfig());
    this.shadowRoot.getElementById("max_history").addEventListener("change", () => this._updateConfig());
    this.shadowRoot.getElementById("profileSelect").addEventListener("change", event => {
      const selected = this._profiles.find(profile => profile.entry_id === event.target.value);
      if (selected) this._applyProfile(selected);
    });
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

  async _loadProfiles() {
    if (!this._hass || this._profilesLoaded || this._profileRequest || typeof this._hass.callWS !== "function") return;
    this._profileRequest = true;
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
    } catch (error) {
      // Keep manual configuration available if the backend profile API is unavailable.
      this._profilesLoaded = true;
      this._manualMode = true;
      this._syncControls();
    } finally {
      this._profileRequest = false;
    }
  }

  _applyProfile(profile, emit = true) {
    const next = {
      ...this._config,
      name: profile.vehicle_name || this._config.name || "EV Charge Tracker",
      profile_entry_id: profile.entry_id,
      entities: { ...(this._config.entities || {}), ...(profile.entities || {}) },
    };
    for (const key of Object.keys(next.entities)) {
      if (!profile.entities?.[key]) delete next.entities[key];
    }
    this._config = next;
    this._manualMode = false;
    this._syncControls();
    if (emit) this._fireConfigChanged();
  }

  _syncControls() {
    if (!this.shadowRoot || !this._built) return;
    const name = this.shadowRoot.getElementById("name");
    const maxHistory = this.shadowRoot.getElementById("max_history");
    if (name && name !== this.shadowRoot.activeElement) name.value = this._config.name || "";
    if (maxHistory && maxHistory !== this.shadowRoot.activeElement) maxHistory.value = this._config.max_history || 8;

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
      profileHint.textContent = this._profiles.length === 1
        ? "Perfil detectado automáticamente."
        : "Selecciona el vehículo y cargador que utilizará esta tarjeta.";
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
    const name = this.shadowRoot.getElementById("name").value.trim() || "EV Charge Tracker";
    const maxHistory = Math.min(50, Math.max(1, Number(this.shadowRoot.getElementById("max_history").value || 8)));
    const next = { ...this._config, name, max_history: maxHistory, entities: { ...(this._config.entities || {}) } };
    if (changedKey) {
      if (changedValue) next.entities[changedKey] = changedValue;
      else delete next.entities[changedKey];
      // A manual override is intentional; do not silently reapply profile defaults.
      next.profile_manual_override = true;
    }
    this._config = next;
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
  name: "EV Charge Tracker",
  description: "Resumen de carga, batería, coste e histórico de vehículo eléctrico.",
  preview: true,
  version: CARD_VERSION,
});
