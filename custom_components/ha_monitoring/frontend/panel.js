// Panneau « Monitoring » (/monitoring) : affiche l'add-on via l'Ingress, comme le panneau
// d'origine de l'add-on, mais à une adresse courte. Reprend ce que fait Home Assistant pour
// ses add-ons : ouvrir une session Ingress, la poser en cookie, la prolonger chaque minute.

const VALIDATE_EVERY = 60 * 1000;
const MENU_ICON =
  "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z"; // mdi:menu

class MonitoringPanel extends HTMLElement {
  constructor() {
    super();
    this._session = null;
    this._timer = null;
    this.attachShadow({ mode: "open" }).innerHTML = `
      <style>
        :host { display: flex; flex-direction: column; height: 100%; }
        .header {
          display: none; align-items: center; gap: 12px; flex: none;
          height: var(--header-height, 56px); padding: 0 12px 0 4px;
          background: var(--app-header-background-color, var(--primary-color));
          color: var(--app-header-text-color, var(--text-primary-color, #fff));
          border-bottom: var(--app-header-border-bottom, none);
          font-size: 20px;
        }
        :host([narrow]) .header { display: flex; }
        button {
          width: 48px; height: 48px; border: 0; border-radius: 50%; padding: 12px;
          background: none; color: inherit; cursor: pointer;
        }
        button:hover { background: rgba(127, 127, 127, 0.15); }
        svg { width: 24px; height: 24px; fill: currentColor; display: block; }
        iframe {
          flex: 1; width: 100%; border: 0; display: block;
          background-color: var(--primary-background-color);
        }
        .message { margin: 24px; color: var(--primary-text-color); }
      </style>
      <div class="header">
        <button title="Menu"><svg viewBox="0 0 24 24"><path d="${MENU_ICON}"></path></svg></button>
        <span class="title">Monitoring</span>
      </div>
      <div class="message" hidden></div>`;
    // Sur téléphone, le panneau n'a pas de bandeau : ce bouton ouvre la barre latérale de HA.
    this.shadowRoot.querySelector("button").addEventListener("click", () => {
      this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
    });
  }

  set narrow(value) {
    this.toggleAttribute("narrow", Boolean(value));
  }

  set panel(panel) {
    this._config = panel.config;
    this.shadowRoot.querySelector(".title").textContent = panel.config.title || "Monitoring";
    this._start();
  }

  set hass(hass) {
    this._hass = hass;
    this._start();
  }

  connectedCallback() {
    this._start();
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    this._timer = null;
    this._started = false;
  }

  _start() {
    if (this._started || !this._hass || !this._config || !this.isConnected) return;
    this._started = true;
    this._open().catch((err) => this._showError(err));
  }

  async _call(endpoint, data) {
    const result = await this._hass.callWS({
      type: "supervisor/api",
      endpoint,
      method: "post",
      ...(data ? { data } : {}),
    });
    return result;
  }

  _setCookie(session) {
    const secure = location.protocol === "https:" ? ";Secure" : "";
    document.cookie =
      `ingress_session=${session};path=/api/hassio_ingress/;SameSite=Strict${secure}`;
  }

  async _newSession() {
    const result = await this._call("/ingress/session");
    this._session = typeof result === "string" ? result : result.session;
    this._setCookie(this._session);
  }

  async _validate() {
    try {
      await this._call("/ingress/validate_session", { session: this._session });
      this._setCookie(this._session);
    } catch {
      await this._newSession(); // session expirée (mise en veille du PC, par exemple)
    }
  }

  async _open() {
    await this._newSession();
    if (!this.isConnected) return;
    clearInterval(this._timer);
    this._timer = setInterval(() => this._validate().catch(() => {}), VALIDATE_EVERY);
    if (!this.shadowRoot.querySelector("iframe")) {
      const frame = document.createElement("iframe");
      frame.title = this._config.title || "Monitoring";
      frame.allow = "fullscreen; clipboard-read; clipboard-write";
      frame.src = this._config.ingress_url;
      this.shadowRoot.appendChild(frame);
    }
    this.shadowRoot.querySelector(".message").hidden = true;
  }

  _showError(err) {
    this._started = false;
    const box = this.shadowRoot.querySelector(".message");
    box.hidden = false;
    box.textContent =
      "Impossible d'ouvrir le monitoring : vérifiez que l'add-on est démarré. " +
      `(${(err && err.message) || err})`;
  }
}

if (!customElements.get("ha-monitoring-panel")) {
  customElements.define("ha-monitoring-panel", MonitoringPanel);
}
