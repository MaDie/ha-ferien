// Karte: heute Schule oder frei, darunter klein ob morgen frei ist.

const ZUORDNUNG = {
  schulfrei_heute: "heute",
  schulfrei_morgen: "morgen",
  grund_heute: "grund",
};

const ICONS = {
  wochenende: "mdi:weather-sunny",
  ferien: "mdi:beach",
  feiertag: "mdi:calendar-star",
  schulfrei: "mdi:school-outline",
  eigener_tag: "mdi:calendar-edit",
};

const TEXTE = {
  de: {
    schule: "Heute ist Schule",
    frei: "Heute ist schulfrei",
    grund: "Grund",
    schultag: "Regulärer Schultag",
    morgenFrei: "Morgen frei",
    morgenSchule: "Morgen Schule",
    keineDaten: "Keine Daten",
    waehlen: "Schulfrei heute wählen",
    name: "Ferien heute",
    beschreibung:
      "Ob heute Schule ist, mit Grund. Darunter klein, ob morgen frei ist.",
    gruende: {
      wochenende: "Wochenende",
      ferien: "Ferien",
      feiertag: "Feiertag",
      schulfrei: "Schulfreier Tag",
      eigener_tag: "Eigener Tag",
    },
  },
  en: {
    schule: "School today",
    frei: "No school today",
    grund: "Reason",
    schultag: "Regular school day",
    morgenFrei: "Free tomorrow",
    morgenSchule: "School tomorrow",
    keineDaten: "No data",
    waehlen: "Choose School-free today",
    name: "Ferien today",
    beschreibung:
      "Whether today is a school day, and why. A smaller line shows tomorrow.",
    gruende: {
      wochenende: "Weekend",
      ferien: "Holidays",
      feiertag: "Public holiday",
      schulfrei: "School-free day",
      eigener_tag: "Custom day",
    },
  },
};

const HTML = `
<style>
  ha-card {
    padding: 28px 16px 22px;
    text-align: center;
    cursor: pointer;
  }
  ha-icon {
    display: block;
    width: 36px;
    height: 36px;
    margin: 0 auto 14px;
    color: var(--primary-color);
  }
  .titel {
    font-size: 1.35rem;
    font-weight: 600;
    line-height: 1.3;
  }
  .grund {
    margin-top: 8px;
    font-size: 1.15rem;
    color: var(--secondary-text-color);
  }
  .morgen {
    margin-top: 10px;
    font-size: 0.8rem;
    line-height: 1.2;
    color: var(--secondary-text-color);
  }
</style>
<ha-card>
  <ha-icon></ha-icon>
  <div class="titel"></div>
  <div class="grund"></div>
  <div class="morgen"></div>
</ha-card>
`;

function deutsch(sprache) {
  return (sprache || "").toLowerCase().startsWith("de");
}

function texte(hass) {
  const sprache = (hass && hass.language) || document.documentElement.lang;
  return deutsch(sprache) ? TEXTE.de : TEXTE.en;
}

function art(eintrag) {
  if (!eintrag) {
    return "";
  }
  if (eintrag.translation_key && ZUORDNUNG[eintrag.translation_key]) {
    return ZUORDNUNG[eintrag.translation_key];
  }
  const unique = eintrag.unique_id || "";
  const entityId = eintrag.entity_id || "";
  for (const key of Object.keys(ZUORDNUNG)) {
    if (unique.endsWith(`_${key}`) || entityId.endsWith(`_${key}`)) {
      return ZUORDNUNG[key];
    }
  }
  return "";
}

function tausche(entityId, domain, schluessel) {
  const rest = entityId.includes(".")
    ? entityId.slice(entityId.indexOf(".") + 1)
    : entityId;
  let stamm = rest;
  for (const alt of Object.keys(ZUORDNUNG)) {
    const ende = `_${alt}`;
    if (rest.endsWith(ende)) {
      stamm = rest.slice(0, -ende.length);
      break;
    }
  }
  return `${domain}.${stamm}_${schluessel}`;
}

function geschwister(hass, entityId) {
  const register = hass.entities || {};
  const selbst = register[entityId];
  const gefunden = {};
  if (selbst) {
    for (const eintrag of Object.values(register)) {
      if (selbst.device_id) {
        if (eintrag.device_id !== selbst.device_id) {
          continue;
        }
      } else if (selbst.config_entry_id) {
        if (eintrag.config_entry_id !== selbst.config_entry_id) {
          continue;
        }
      } else {
        continue;
      }
      if (eintrag.platform && eintrag.platform !== "ferien") {
        continue;
      }
      const rolle = art(eintrag);
      if (rolle) {
        gefunden[rolle] = eintrag.entity_id;
      }
    }
  }
  if (!gefunden.heute) {
    gefunden.heute = tausche(entityId, "binary_sensor", "schulfrei_heute");
  }
  if (!gefunden.morgen) {
    gefunden.morgen = tausche(gefunden.heute, "binary_sensor", "schulfrei_morgen");
  }
  if (!gefunden.grund) {
    gefunden.grund = tausche(gefunden.heute, "sensor", "grund_heute");
  }
  return gefunden;
}

function lesbar(zustand) {
  return (
    zustand &&
    zustand !== "unknown" &&
    zustand !== "unavailable" &&
    zustand !== "none"
  );
}

function schluessel(hass, ids) {
  const sensor = hass.states[ids.grund];
  const bin = hass.states[ids.heute];
  const aus = (eintrag) => eintrag && eintrag.attributes && eintrag.attributes.grund;
  return aus(sensor) || aus(bin) || "";
}

function nameHeute(hass, ids, t) {
  const key = schluessel(hass, ids);
  if (key === "wochenende") {
    return t.gruende.wochenende;
  }
  const sensor = hass.states[ids.grund];
  if (sensor && lesbar(sensor.state)) {
    return t.gruende[sensor.state] || sensor.state;
  }
  const bin = hass.states[ids.heute];
  const name = bin && bin.attributes && bin.attributes.name;
  if (name) {
    return name;
  }
  return t.gruende[key] || "";
}

function anzeige(hass, entityId) {
  const t = texte(hass);
  if (!entityId) {
    return { icon: "mdi:school", titel: t.waehlen, grund: "", morgen: "", ziel: "" };
  }
  const ids = geschwister(hass, entityId);
  const heute = hass.states[ids.heute] && hass.states[ids.heute].state;
  const morgen = hass.states[ids.morgen] && hass.states[ids.morgen].state;
  let icon = "mdi:school-outline";
  let titel = t.keineDaten;
  let grund = "";
  if (heute === "off") {
    icon = "mdi:school";
    titel = t.schule;
    grund = `${t.grund}: ${t.schultag}`;
  } else if (heute === "on") {
    const key = schluessel(hass, ids);
    icon = ICONS[key] || "mdi:beach";
    titel = t.frei;
    const name = nameHeute(hass, ids, t);
    if (name) {
      grund = `${t.grund}: ${name}`;
    }
  }
  let klein = "";
  if (morgen === "on") {
    klein = t.morgenFrei;
  } else if (morgen === "off") {
    klein = t.morgenSchule;
  }
  return { icon, titel, grund, morgen: klein, ziel: ids.heute };
}

class FerienHeuteKarte extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = { entity: "" };
    this._signatur = "";
    this._ziel = "";
  }

  setConfig(config) {
    this._config = { entity: (config && config.entity) || "" };
    this._signatur = "";
    if (this._hass) {
      this._zeichnen();
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._zeichnen();
  }

  getCardSize() {
    return 3;
  }

  static getConfigForm() {
    return {
      schema: [
        {
          name: "entity",
          required: true,
          selector: {
            entity: {
              filter: [{ integration: "ferien", domain: "binary_sensor" }],
            },
          },
        },
      ],
    };
  }

  static getStubConfig() {
    return {};
  }

  _zeichnen() {
    if (!this.shadowRoot.querySelector("ha-card")) {
      this.shadowRoot.innerHTML = HTML;
      this.shadowRoot.querySelector("ha-card").addEventListener("click", () => {
        if (!this._ziel || !this._hass.states[this._ziel]) {
          return;
        }
        this.dispatchEvent(
          new CustomEvent("hass-more-info", {
            bubbles: true,
            composed: true,
            detail: { entityId: this._ziel },
          }),
        );
      });
    }
    const stand = anzeige(this._hass, this._config.entity);
    const signatur = JSON.stringify(stand);
    if (signatur === this._signatur) {
      return;
    }
    this._signatur = signatur;
    this._ziel = stand.ziel;
    const wurzel = this.shadowRoot;
    const icon = wurzel.querySelector("ha-icon");
    icon.icon = stand.icon;
    wurzel.querySelector(".titel").textContent = stand.titel;
    const grund = wurzel.querySelector(".grund");
    grund.textContent = stand.grund;
    grund.hidden = !stand.grund;
    const morgen = wurzel.querySelector(".morgen");
    morgen.textContent = stand.morgen;
    morgen.hidden = !stand.morgen;
  }
}

customElements.define("ferien-heute-karte", FerienHeuteKarte);

const sprache = document.documentElement.lang;
const t = deutsch(sprache) ? TEXTE.de : TEXTE.en;
window.customCards = window.customCards || [];
window.customCards.push({
  type: "ferien-heute-karte",
  name: t.name,
  description: t.beschreibung,
  preview: true,
});
