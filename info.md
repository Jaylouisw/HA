# HAIMish

**Home Assistant Internet Map (ish)**

See where the Home Assistant community is deployed around the world and visualize the network paths between us!

## Quick Start

1. Install via HACS
2. Restart Home Assistant  
3. Add integration: **Settings** → **Devices & Services** → **Add Integration** → **HAIMish**
4. Add the map card to your dashboard

That's it! Your node will automatically discover other HAIMish peers via BitTorrent DHT.

## What You'll See

- 🗺️ Community deployments on a world map
- 🌐 Network topology links between peers
- 📡 Traceroute paths with geographic hop visualization
- 🏢 ASN/IXP/Datacenter identification for each hop

## Privacy

- Location is fuzzed by default (~10km radius)
- Anonymous mode available
- No central server - fully P2P
- Privacy settings have 24h cooldown to prevent abuse
