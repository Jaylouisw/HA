# HAIMish

**Home Assistant Internet Map (ish)**

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/jaylouisw/HA.svg)](https://github.com/jaylouisw/HA/releases)
[![License](https://img.shields.io/github/license/jaylouisw/HA.svg)](LICENSE)

> **Note**: This README is kept for reference. See the main [README.md](../README.md) for current documentation.

A Home Assistant custom integration that displays community Home Assistant deployments on a geographical map and visualizes network topology between participating instances.

## Features

- 🗺️ **Geographic Map**: See where Home Assistant deployments are located worldwide
- 🌐 **Network Topology**: Visualize network paths between community members
- 📡 **Traceroute**: Run traceroutes between instances with full hop enrichment
- 🔒 **Privacy First**: Location fuzzing, anonymous mode, daily toggle cooldowns
- 🔄 **Zero Config Discovery**: Automatic peer finding via BitTorrent DHT & IPFS
- 🕸️ **Fully Distributed**: No central server - pure P2P gossip protocol
- 🌍 **IP Intelligence**: ASN tracking, IXP detection, datacenter identification
- 🎨 **Custom Lovelace Card**: Beautiful map visualization using Leaflet.js

## How It Works

HAIMish uses a **fully distributed P2P architecture** - no central server required:

1. **BitTorrent DHT Discovery**: Nodes announce themselves to the global BitTorrent DHT (the same network used by millions of torrent clients)
2. **IPFS PubSub** (optional): If you run IPFS locally, nodes also discover via pub/sub
3. **Gossip Protocol**: Once connected, nodes share peer lists and topology data
4. **Dynamic Ports**: Like BitTorrent, nodes use auto-assigned ports and advertise them during discovery

The first two HAIMish nodes ever will find each other through the global DHT - requiring zero infrastructure from us!

## Installation

### HACS (One-Click Install) ⭐ Recommended

1. Open HACS in Home Assistant
2. Click **⋮** → **Custom repositories**
3. Add: `https://github.com/jaylouisw/HA`
4. Category: **Integration**
5. Find **HAM Network Map** and click **Download**
6. Restart Home Assistant

### Manual Installation

1. Download `ham_network.zip` from the [latest release](https://github.com/jaylouisw/HA/releases)
2. Extract `custom_components/ham_network` to your HA `config/custom_components/`
3. Extract `www/ham-network-map/` to your HA `config/www/`
4. Restart Home Assistant

## Configuration

### Integration Setup

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "HAM Network Map"
4. Enter your configuration:
   - **Display Name**: How your instance appears on the map
   - **Latitude/Longitude**: Your location (defaults to HA config)
   - **Public URL** (optional): Your public Home Assistant URL
   - **Discovery Server**: URL of the discovery server
   - **Share Location**: Whether to share your location with the community

### Lovelace Card

Add the custom card resource to your Lovelace configuration:

```yaml
resources:
  - url: /local/ham-network-map/ham-network-map.js
    type: module
```

Then add the card to your dashboard:

```yaml
type: custom:ham-network-map
entity: sensor.ham_network_map_network_topology
title: Community Network Map
height: 500px
zoom: 4
show_topology: true
show_traceroute: true
```

#### Card Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `entity` | string | *required* | The topology sensor entity |
| `title` | string | "HAM Network Map" | Card title |
| `height` | string | "400px" | Map height |
| `zoom` | number | 4 | Default zoom level (1-18) |
| `show_topology` | boolean | true | Show network links |
| `show_traceroute` | boolean | true | Show traceroute paths |
| `marker_color` | string | "#03a9f4" | Peer marker color |
| `my_marker_color` | string | "#4caf50" | Your marker color |
| `link_color` | string | "#ff9800" | Network link color |

## Services

### `ham_network.traceroute`

Run a traceroute to one or all peers.

```yaml
service: ham_network.traceroute
data:
  target_peer: "peer-uuid"  # Optional, omit to traceroute all
```

### `ham_network.refresh_peers`

Force refresh the peer list from the discovery server.

```yaml
service: ham_network.refresh_peers
```

## Sensors

The integration creates the following sensors:

| Sensor | Description |
|--------|-------------|
| `sensor.ham_network_map_connected_peers` | Number of connected peers |
| `sensor.ham_network_map_network_topology` | Full topology data |
| `sensor.ham_network_map_status` | Connection status |

## Network Architecture

### Decentralized Discovery

HAM Network uses multiple discovery methods that require **no central server**:

| Method | Description |
|--------|-------------|
| **BitTorrent DHT** | Primary discovery via the global mainline DHT |
| **IPFS PubSub** | Secondary discovery if IPFS daemon is running |
| **DNS Bootstrap** | Fallback for community-maintained bootstrap nodes |

### Port Handling

Like BitTorrent, HAM Network uses **dynamic port assignment**:

- Default: Port is auto-assigned by the OS (port=0)
- Nodes advertise their actual port via DHT announcements
- Users can optionally configure a fixed port for NAT/firewall rules
- Each node runs two services: P2P HTTP server + DHT UDP listener

### IP Intelligence

Every traceroute hop is enriched with:

- **Geolocation**: City, country, coordinates
- **ASN Info**: Provider network, organization
- **IXP Detection**: Internet Exchange Points
- **Datacenter ID**: AWS, GCP, Azure, Cloudflare, etc.
- **CDN Detection**: Content delivery networks

## Privacy

Your privacy is protected by design:

- **Location Fuzzing**: Coordinates randomized within configurable radius
- **Anonymous Mode**: Participate without sharing any location
- **Toggle Cooldown**: Privacy settings can only change once per 24 hours
- **No Central Server**: Your data isn't stored anywhere centrally
- **Contribution-based Access**: Only contributing peers see full topology

### Privacy Settings

| Setting | Description |
|---------|-------------|
| `share_location` | Whether to share your (fuzzed) location |
| `anonymous_contributions` | Contribute traceroutes without identity |
| `location_fuzzing_km` | Radius for location randomization (default: 10km) |

## Development

### Project Structure

```
custom_components/
  ham_network/
    __init__.py          # Integration setup
    manifest.json        # HA integration manifest
    config_flow.py       # Configuration UI
    const.py             # Constants
    coordinator.py       # Data update coordinator
    sensor.py            # Sensor entities
    services.yaml        # Service definitions
    api.py               # API client for peer communication
    network.py           # Traceroute and network utilities
    ip_intel.py          # IP intelligence (geo, ASN, IXP)
    privacy.py           # Privacy manager with daily cooldown
    p2p.py               # P2P distributed peer discovery
    discovery.py         # Auto-discovery via DHT/IPFS
    strings.json         # UI strings
    translations/
      en.json            # English translations
www/
  ham-network-map/
    ham-network-map.js   # Lovelace card with Leaflet map
```

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Credits

- [Leaflet.js](https://leafletjs.com/) for map rendering
- [Home Assistant](https://www.home-assistant.io/) for the amazing platform
- The Home Assistant community for inspiration
