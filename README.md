# Jay's Home Assistant Projects

<p align="center">
  <img src="https://www.home-assistant.io/images/home-assistant-logo.svg" alt="Home Assistant" width="150">
</p>

<p align="center">
  Custom integrations, add-ons, and tools for Home Assistant
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Badge"></a>
  <a href="https://github.com/jaylouisw/HA/releases"><img src="https://img.shields.io/github/release/jaylouisw/HA.svg" alt="GitHub Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/jaylouisw/HA.svg" alt="License"></a>
</p>

---

## 📦 Projects

### HAIMish — Home Assistant Internet Map (ish)

<a href="HAIMish/">
  <img src="HAIMish/images/banner.png" alt="HAIMish" width="500">
</a>

**See where the Home Assistant community is deployed around the world!**

A fully distributed P2P integration that maps HA deployments globally and visualizes network topology between them. Zero central server — pure BitTorrent DHT + gossip protocol.

**Features:**
- 🗺️ Global map of HA deployments
- 🌐 Network topology visualization
- 📡 Traceroute with geographic hop enrichment
- 🔒 Privacy first (location fuzzing, anonymous mode)
- 🔄 Zero config peer discovery via BitTorrent DHT

➡️ **[View HAIMish Documentation](HAIMish/)**

---

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

## 🚀 Installation (via HACS)

1. Open **HACS** → **Integrations**
2. Click **⋮** → **Custom repositories**
3. Add URL: `https://github.com/jaylouisw/HA`
4. Category: **Integration**
5. Find the integration you want and click **Download**
6. **Restart Home Assistant**

---

## 🗂️ Repository Structure

```
jaylouisw/HA/
├── .github/workflows/     # CI/CD (HACS validation, releases)
├── HAIMish/               # HAIMish integration
│   ├── custom_components/haimish/
│   ├── www/haimish-map/
│   └── README.md
├── HAGrid/                # HAGrid integration
│   ├── custom_components/hagrid/
│   ├── www/hagrid-map/
│   └── README.md
├── hacs.json              # HACS configuration
└── README.md              # This file
```

---

## 🔮 Coming Soon

More Home Assistant projects in development:

- **HAMarket** — P2P marketplace for smart home devices

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <sub>Built with ❤️ for the Home Assistant community</sub>
</p>
