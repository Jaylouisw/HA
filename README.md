# HAIMish

**Home Assistant Internet Map (ish)**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/jaylouisw/HA.svg)](https://github.com/jaylouisw/HA/releases)
[![License](https://img.shields.io/github/license/jaylouisw/HA.svg)](LICENSE)

See where the Home Assistant community is deployed around the world and visualize the network paths between us!

![HAIMish Map Preview](https://via.placeholder.com/800x400?text=HAIMish+Map+Preview)

## ✨ Features

- 🗺️ **Global Map** — See HA deployments worldwide on an interactive map
- 🌐 **Network Topology** — Visualize network paths between community members
- 📡 **Traceroute Visualization** — Run and visualize traceroutes with geographic hop data
- 🔒 **Privacy First** — Location fuzzing, anonymous mode, no central server
- 🔄 **Zero Config** — Automatic peer discovery via BitTorrent DHT
- 🕸️ **Fully Distributed** — Pure P2P architecture, no infrastructure required
- 🏢 **IP Intelligence** — ASN, IXP, datacenter, and cell tower identification
- 📱 **Mobile Support** — Traceroute from your phone back to your HA
- ⚡ **Scalable** — DHT-based sharding handles millions of nodes

---

## 🚀 Quick Start

### Install via HACS

1. Open **HACS** → **Integrations**
2. Click **⋮** → **Custom repositories**
3. Add URL: `https://github.com/jaylouisw/HA`
4. Category: **Integration**
5. Search for **HAIMish** and click **Download**
6. **Restart Home Assistant**

### Configure

1. **Settings** → **Devices & Services** → **Add Integration**
2. Search for **HAIMish**
3. Enter your display name and location
4. Done! You'll start discovering peers automatically

### Add the Map Card

```yaml
type: custom:haimish-map
title: HAIMish
height: 500px
show_topology: true
show_traceroute: true
```

---

## 🏗️ Architecture

HAIMish uses a **fully distributed P2P architecture** — no central server required:

```
┌─────────────┐     BitTorrent DHT      ┌─────────────┐
│   Your HA   │◄──────────────────────►│  Other HA   │
│  Instance   │                         │  Instances  │
└──────┬──────┘                         └──────┬──────┘
       │                                       │
       │         P2P Gossip Protocol           │
       └───────────────────────────────────────┘
                        │
              ┌─────────┴─────────┐
              │   Shared Data     │
              │  - Peer locations │
              │  - Traceroutes    │
              │  - Infrastructure │
              └───────────────────┘
```

### How Discovery Works

1. **BitTorrent DHT** — Nodes announce to the global DHT (same network as BitTorrent)
2. **Gossip Protocol** — Connected peers share peer lists and data
3. **Dynamic Ports** — Auto-assigned ports, advertised via DHT
4. **Geographic Sharding** — Nodes only store data for their region

The first two HAIMish nodes ever will find each other through the global DHT!

---

## 🛡️ Privacy

Your privacy is protected by design:

| Feature | Description |
|---------|-------------|
| **Location Fuzzing** | Coordinates randomized within ~10km (configurable) |
| **Anonymous Mode** | Participate without sharing any identifying info |
| **24h Toggle Cooldown** | Privacy settings can only change once per day |
| **No Central Server** | Your data isn't stored anywhere you don't control |
| **Data Sharing Off by Default** | Opt-in to share traceroutes with the network |

### Privacy Settings

```yaml
# In the integration config:
share_location: true           # Share fuzzed location on map
location_fuzzing_km: 10        # Fuzzing radius in km
anonymous_mode: false          # Hide display name
share_traceroute_data: false   # Share traceroutes with network (default: off)
```

---

## 🌍 IP Intelligence

Every traceroute hop is enriched with:

| Data | Source | Example |
|------|--------|---------|
| **Geolocation** | IP-API | London, UK (51.5, -0.1) |
| **ASN** | BGP | AS13335 - Cloudflare |
| **IXP** | PeeringDB | LINX LON1 |
| **Datacenter** | Infrastructure DB | Equinix LD4 |
| **Cell Tower** | Mobile Detection | EE 4G Tower |

### Infrastructure Database

HAIMish includes a comprehensive database of:
- 🔀 Internet Exchange Points (IXPs) — DE-CIX, LINX, AMS-IX, etc.
- 🏢 Major Datacenters — Equinix, Interxion, Digital Realty
- 📞 Telecom Exchanges — BT exchanges across the UK
- 🌊 Cable Landing Stations — Submarine cable endpoints
- 📱 Mobile Networks — Cell tower detection via CGNAT/ASN

---

## 📊 Scalability

HAIMish is designed to scale to millions of nodes:

### DHT-Based Sharding

```
Data Type          │ TTL      │ Replication │ Storage
───────────────────┼──────────┼─────────────┼────────────────
Infrastructure     │ Forever  │ 5+ nodes    │ All nodes
Peer Locations     │ 1 hour   │ 3 nodes     │ Nearby nodes
Traceroutes        │ 24 hours │ 3 nodes     │ Nearby nodes
```

- **Geographic Partitioning** — Nodes only store data for their region
- **On-Demand Loading** — Data fetched when viewing different map regions
- **Node Decay** — Disconnected peers fade from map over 1 hour

---

## 🔧 Services

### `haimish.traceroute`

Run a traceroute to a peer:

```yaml
service: haimish.traceroute
data:
  target_peer: "peer-uuid"  # Optional - omit to trace all peers
```

### `haimish.refresh_peers`

Force refresh the peer list:

```yaml
service: haimish.refresh_peers
```

---

## 📈 Sensors

| Sensor | Description |
|--------|-------------|
| `sensor.haimish_connected_peers` | Number of connected peers |
| `sensor.haimish_network_topology` | Full topology data (for map card) |
| `sensor.haimish_status` | Connection status |

---

## 🎨 Lovelace Card Options

```yaml
type: custom:haimish-map
entity: sensor.haimish_network_topology
title: HAIMish
height: 500px
zoom: 4
show_topology: true
show_traceroute: true
marker_color: "#03a9f4"
my_marker_color: "#4caf50"
link_color: "#ff9800"
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `entity` | string | required | Topology sensor entity |
| `title` | string | "HAIMish" | Card title |
| `height` | string | "400px" | Map height |
| `zoom` | number | 4 | Default zoom (1-18) |
| `show_topology` | boolean | true | Show network links |
| `show_traceroute` | boolean | true | Show traceroute paths |
| `show_infrastructure` | boolean | true | Show IXPs/datacenters |
| `marker_color` | string | "#03a9f4" | Peer marker color |
| `my_marker_color` | string | "#4caf50" | Your marker color |

---

## 🔌 Manual Installation

If you prefer not to use HACS:

1. Download from [Releases](https://github.com/jaylouisw/HA/releases)
2. Copy `custom_components/haimish/` to your `config/custom_components/`
3. Copy `www/haimish-map/` to your `config/www/`
4. Add the Lovelace resource:
   ```yaml
   resources:
     - url: /local/haimish-map/haimish-map.js
       type: module
   ```
5. Restart Home Assistant

---

## 🛠️ Development

### Project Structure

```
custom_components/haimish/
├── __init__.py         # Integration setup
├── manifest.json       # HA integration manifest
├── config_flow.py      # Configuration UI
├── const.py            # Constants
├── coordinator.py      # Data update coordinator
├── sensor.py           # Sensor entities
├── api.py              # Peer communication
├── network.py          # Traceroute utilities
├── ip_intel.py         # IP intelligence (geo, ASN, IXP)
├── infrastructure_db.py # IXP/datacenter/cell tower database
├── privacy.py          # Privacy manager
├── p2p.py              # P2P node & gossip protocol
├── discovery.py        # BitTorrent DHT discovery
├── sharding.py         # DHT-based distributed storage
└── translations/
    └── en.json

www/haimish-map/
└── haimish-map.js  # Lovelace card (Leaflet.js)
```

### DHT Info Hash

All HAIMish nodes announce to the same DHT info_hash:
```
SHA1("haimish-homeassistant-community-map-v1")
= (backwards compatible with original hash)
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Credits

- Built for the Home Assistant community
- Uses [Leaflet.js](https://leafletjs.com/) for maps
- BitTorrent DHT via mainline DHT bootstrap nodes
- IP geolocation via [ip-api.com](https://ip-api.com/)

---

**Made with ❤️ for the Home Assistant community**
