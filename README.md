# Jay's Home Assistant Projects

<p align="center">
  <img src="https://www.home-assistant.io/images/home-assistant-logo.svg" alt="Home Assistant" width="150">
</p>

<p align="center">
  Custom integrations and tools for Home Assistant
</p>

<p align="center">
  <a href="https://github.com/jaylouisw/HA/releases"><img src="https://img.shields.io/github/release/jaylouisw/HA.svg" alt="GitHub Release"></a>
</p>

---

## 📦 Projects

### HAGrid — UK Electrical Grid Map 🔌

**Bring the UK electrical grid into your Home Assistant dashboard!**

Real-time carbon intensity, generation mix, live faults, and interactive infrastructure maps powered by the Carbon Intensity API and UK Power Networks open data.

**Features:**
- 📊 Real-time carbon intensity with 48hr forecast
- ⚡ Generation mix (wind, solar, gas, nuclear, etc.)
- 🗺️ Interactive map with substations & power lines
- 🚨 Live fault monitoring and outage alerts
- 🌿 "Best time" recommendations for low-carbon usage

➡️ **[View HAGrid Documentation](HAGrid/)**

---

## 🚀 Installation

HAGrid is **not installable through HACS from this repository yet** — the integration sits under
[`HAGrid/custom_components/hagrid`](HAGrid/custom_components/hagrid) rather than at the repository
root, which is where HACS looks. Until that is fixed, install it manually:

1. Copy [`HAGrid/custom_components/hagrid`](HAGrid/custom_components/hagrid) into your Home Assistant
   `config/custom_components/hagrid` directory — the folder must be named exactly `hagrid`.
2. Copy [`HAGrid/www/hagrid-map`](HAGrid/www/hagrid-map) into `config/www/hagrid-map`.
3. **Restart Home Assistant.**
4. Go to **Settings** → **Devices & Services** → **Add Integration** → **HAGrid**.

If the config flow reports *"Invalid handler specified"*, the integration folder is almost always
named wrongly — it must be `config/custom_components/hagrid/`, with `manifest.json` inside it.

---

## 🗂️ Repository Structure

```
jaylouisw/HA/
├── .github/workflows/     # CI (HACS validation, releases)
├── HAGrid/                # HAGrid integration
│   ├── custom_components/hagrid/
│   ├── www/hagrid-map/
│   └── README.md
├── hacs.json              # HACS configuration
└── README.md              # This file
```

---

## 📄 License

MIT License — see [HAGrid/LICENSE](HAGrid/LICENSE) for details.

---

<p align="center">
  <sub>Built with ❤️ for the Home Assistant community</sub>
</p>
