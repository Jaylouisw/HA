<!-- Home Assistant Map (HAM) - Community Network Topology Integration -->

# Project: Home Assistant Community Map & Network Topology

## Overview
A Home Assistant custom integration that:
1. Shows Home Assistant deployments on a geographical map
2. Performs traceroute between participating instances
3. Visualizes network topology between community members
4. Geographically enriches each hop with ASN, IXP, and datacenter detection
5. Respects user privacy with daily toggle cooldowns and location fuzzing

## Tech Stack
- Python 3.11+ (Home Assistant integration)
- Home Assistant Custom Component structure
- Leaflet.js for map visualization
- P2P distributed peer discovery (no central server)
- IP Intelligence (geo-location, ASN lookup, IXP detection)

## Project Structure
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

## Features
- **Privacy First**: Toggle-able settings with 24-hour cooldown, location fuzzing
- **Zero Config Discovery**: Automatic peer finding via BitTorrent DHT and IPFS
- **Distributed P2P**: No central server dependency, gossip protocol
- **Network Path Visualization**: Geographic hop enrichment on traceroute
- **ASN Tracking**: Provider network identification, ASN transitions
- **Infrastructure Detection**: IXPs, datacenters, cloud providers, CDNs
- **Leaderboard**: Optional anonymous participation

## Auto-Discovery
HAM Network uses decentralized discovery so nodes can find each other without any central server:

1. **BitTorrent DHT** - Primary method. All HAM nodes announce to the same info_hash in the global DHT.
2. **IPFS PubSub** - If IPFS is running locally, nodes subscribe to a shared topic.
3. **DNS Bootstrap** - Fallback for community-maintained bootstrap nodes.

The first two nodes ever will find each other through the BitTorrent DHT - a network of millions of nodes
that requires zero infrastructure from us.

## Checklist

- [x] Verify copilot-instructions.md created
- [x] Scaffold the Project
- [x] Customize the Project
- [x] Install Required Extensions
- [x] Compile the Project
- [x] IP Intelligence module (geo, ASN, IXP detection)
- [x] Network path enrichment integration
- [x] Lovelace card with path visualization
- [x] Dynamic port handling (BitTorrent-style)
- [x] Ensure Documentation is Complete
- [ ] Create and Run Task
- [ ] Launch the Project
