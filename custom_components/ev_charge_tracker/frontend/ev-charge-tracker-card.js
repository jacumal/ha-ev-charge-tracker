/* EV Charge Tracker Lovelace card
 * Copyright (c) EV Charge Tracker contributors. MIT.
 */
const CARD_VERSION = "0.1.0";

class EVChargeTrackerCard extends HTMLElement {
  setConfig(config) {
    // Home Assistant calls setConfig with the stub while the user is still
    // configuring the card. Keep incomplete configurations editable.
    this.config = { ...config, entities: { ...(config?.entities || {}) } };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this.shadowRoot) this._render();
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
    const status = this._value(e.status, "idle");
    const statusLabels = {
      idle: "En espera", charging: "Cargando", finishing: "Finalizando",
      pending_finalization: "Pendiente de confirmar", completed: "Completada",
      needs_attention: "Revisar datos",
    };
    const charging = status === "charging";
    const energy = this._number(e.energy);
    const cost = this._number(e.cost);
    const rawKnownCost = this._attr(e.cost, "known_cost", null);
    const knownCost = rawKnownCost === null || rawKnownCost === undefined ? null : Number(rawKnownCost);
    const hasKnownCost = knownCost !== null && Number.isFinite(knownCost);
    const socStart = this._number(e.soc_start);
    const socEnd = this._number(e.soc_end);
    const increase = this._number(e.soc_increase);
    const duration = this._number(e.duration);
    const history = this._attr(e.history, "sessions", []);
    const current = this._attr(e.history, "current_session", null);
    const latest = this._attr(e.history, "latest_session", null);
    const diagnostic = this._attr(e.history, "diagnostic", "");
    const record = current || latest || {};
    const currency = this._attr(e.cost, "currency", this._state(e.cost)?.attributes?.unit_of_measurement || "EUR");
    const costStatus = this._attr(e.cost, "cost_status", record.cost_status || "unknown");
    const tariffEstimated = this._attr(e.cost, "tariff_estimated", record.tariff_estimated || false);
    const energyUnit = this._attr(e.energy, "unit_of_measurement", "kWh");
    const title = this.config.name || this.config.vehicle || "EV Charge Tracker";
    const start = this._date(record.started_at);
    const end = this._date(record.ended_at || record.completed_at);
    const rows = Array.isArray(history) ? history.slice(0, Number(this.config.max_history || 8)) : [];

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
        .latest { margin-top:20px; padding:17px; border-radius:17px; background:var(--secondary-background-color); }
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
        @media(max-width:420px) { .wrap{padding:15px}.ring{width:72px;height:72px}.ring span{font-size:19px}.metric{padding:10px 8px}.metric strong{font-size:17px}.row{grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr) minmax(0,.8fr)} }
      </style>
      <ha-card>
        <div class="wrap">
          <div class="top">
            <div><div class="eyebrow">Cargas · Última carga</div><h2>${this._escape(title)}</h2></div>
            <div class="status ${charging ? "active" : (status.includes("pending") || status.includes("attention") ? "warn" : "")}">
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
              <div class="metric"><strong>${tariffEstimated ? "Estimado" : "Medido"}</strong><span>Reparto tarifa</span></div>
            </div>
            <div class="dates">
              <div class="date">Inicio<b>${start}</b></div>
              <div class="date">Fin<b>${current && !record.ended_at ? "En curso" : end}</b></div>
            </div>
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
  setConfig(config) { this._config = config || {}; this._render(); }
  set hass(hass) { this._hass = hass; this._render(); }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const fields = [
      ["status","Estado de carga"],["energy","Energía de la carga"],["cost","Coste de la carga"],
      ["soc_start","Batería al inicio"],["soc_end","Batería al final"],["soc_increase","Aumento de batería"],
      ["duration","Duración"],["history","Histórico de cargas"],
    ];
    this.shadowRoot.innerHTML = `<style>
      .field{display:block;margin:12px 0} label{display:block;margin-bottom:5px;font-size:13px}
      input{box-sizing:border-box;width:100%;padding:9px;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color)}
    </style><div>
      <label class="field">Nombre visible<input id="name" value="${this._esc(this._config.name || "")}" placeholder="Leapmotor C10"></label>
      ${fields.map(([key,label]) => `<label class="field">${label}<input data-key="${key}" value="${this._esc(this._config.entities?.[key] || "")}" placeholder="sensor...."></label>`).join("")}
      <label class="field">Máximo de cargas históricas<input id="max_history" type="number" min="1" max="50" value="${this._config.max_history || 8}"></label>
    </div>`;
    this.shadowRoot.querySelectorAll("input").forEach(input => input.addEventListener("change", () => {
      const next = { ...this._config, name: this.shadowRoot.getElementById("name").value,
        max_history: Number(this.shadowRoot.getElementById("max_history").value || 8),
        entities: { ...(this._config.entities || {}) } };
      this.shadowRoot.querySelectorAll("[data-key]").forEach(field => {
        if (field.value.trim()) next.entities[field.dataset.key] = field.value.trim();
        else delete next.entities[field.dataset.key];
      });
      this._config = next;
      this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: next }, bubbles: true, composed: true }));
    }));
  }
  _esc(value) { return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
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
