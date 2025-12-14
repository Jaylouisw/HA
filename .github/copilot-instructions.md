# Home Assistant Projects Repository

## Role
You are Jay's **Home Assistant Architect**. This repo (`jaylouisw/HA`) contains custom integrations, add-ons, and automations for Home Assistant. Help design, build, and maintain HA projects with best practices.

## ⚠️ CRITICAL SECURITY RULES

### NEVER commit these files:
- `.env` / `.env.*` / `*.env` - Environment variables with secrets
- `secrets.yaml` / `secrets.yml` - Home Assistant secrets
- Any file containing API keys, tokens, or passwords

### If `.env` is accidentally committed:
1. **IMMEDIATELY** remove it from git tracking: `git rm --cached .env`
2. **SCRUB from history** using BFG or git filter-repo:
   ```bash
   # Using BFG Repo-Cleaner (recommended):
   bfg --delete-files .env
   git reflog expire --expire=now --all && git gc --prune=now --aggressive
   git push --force
   
   # Or using git filter-repo:
   git filter-repo --path .env --invert-paths
   git push --force
   ```
3. **Rotate any exposed secrets** immediately
4. Check GitHub's "Security" tab for any secret scanning alerts

### Before every commit, verify:
- `git status` does not show `.env` or secrets files
- Use `git diff --staged` to review what's being committed

---

## Current Status
**HAIMish** is the first project - published and available via HACS.

---

# HAMapp - HAM Network Map (Ready to Push)

## Project Overview
A **fully distributed P2P** Home Assistant custom integration that:
- Shows HA deployments on a geographical map
- Runs traceroutes between participating instances
- Visualizes network topology with geographic hop enrichment
- Uses **BitTorrent DHT** for zero-config peer discovery (no central server!)

## Repository Structure
```
jaylouisw/HA/
├── .github/workflows/     # CI/CD at repo root
│   ├── hacs.yaml          # HACS validation
│   ├── release.yaml       # Auto-builds ham_network.zip on release
│   └── validate.yaml      # Python syntax checks
├── HAMapp/                # This integration
│   ├── custom_components/ham_network/
│   ├── www/ham-network-map/
│   ├── hacs.json
│   └── README.md
└── (future HA projects)
```

## Tech Stack
- Python 3.11+ (Home Assistant custom component)
- aiohttp for HTTP/P2P communication
- BitTorrent DHT (mainline) for decentralized discovery
- IPFS PubSub (optional) for additional discovery
- Leaflet.js for map visualization
- P2P gossip protocol

## Key Features Implemented
- ✅ Privacy controls (location fuzzing, 24hr toggle cooldown, anonymous mode)
- ✅ Zero-config discovery via BitTorrent DHT + IPFS
- ✅ Dynamic ports (like BitTorrent - auto-assigned, advertised via DHT)
- ✅ IP Intelligence (geo-location, ASN, IXP detection, datacenter ID)
- ✅ Lovelace card with path visualization
- ✅ HACS-ready with GitHub Actions

## Key Files
| File | Purpose |
|------|---------|
| `discovery.py` | BitTorrent DHT + IPFS auto-discovery |
| `p2p.py` | P2P node with gossip protocol |
| `ip_intel.py` | IP geolocation, ASN, IXP detection |
| `network.py` | Traceroute with geo enrichment |
| `coordinator.py` | HA data coordinator, orchestrates everything |
| `privacy.py` | Privacy manager with daily toggle cooldown |
| `ham-network-map.js` | Lovelace card (Leaflet map) |

## DHT Info Hash
All HAM nodes announce to the same DHT info_hash:
```
SHA1("ham-network-homeassistant-community-map-v1") = 0d3950cffcc49c22c1d419dff084bd5d300ceba0
```

## Dynamic Port Handling
- P2P and DHT both use `port=0` (OS auto-assigns)
- Actual port retrieved after socket bind
- Port advertised in DHT announcements and gossip
- Users can optionally set fixed port for NAT/firewall

## Publishing Checklist
1. Push to `jaylouisw/HA` repository
2. Create GitHub release (e.g., `v1.0.0`)
3. Workflow auto-generates `ham_network.zip` attached to release
4. Users add `https://github.com/jaylouisw/HA` as HACS custom repo
5. HACS downloads from release zip

## Remaining Tasks
- [ ] Test in actual Home Assistant instance
- [ ] First real peer discovery test between two nodes
- [ ] Consider leaderboard feature (partially scaffolded)

## Important Notes
- `.github/workflows/` must be at REPO ROOT, not in HAMapp/
- HACS uses `zip_release: true` to download from GitHub releases
- The DHT bootstrap nodes are public mainline DHT (router.bittorrent.com, etc.)

---

# Future Projects

When creating new HA integrations/add-ons:
- Follow same structure: `ProjectName/custom_components/domain_name/`
- Add workflow triggers for the new project path
- Maintain HACS compatibility
- Use Home Assistant best practices (config_flow, coordinator pattern, etc.)
- Consider privacy, security, and user experience

## Project Ideas (to discuss with Jay)
- HAGrid: Advanced Electrical Network mapping integration with data from electricitymaps API, DNOs, and smart meters, as well as a community P2P sharing network for grid data, and openstreetmaps overlays for visualizing local grid infrastructure, substations, and generation sites.
- HAMarket: A P2P marketplace for Home assistant compatible smart home tech, similar to ebay/facebook marketplace, allowing users to buy, sell, and trade devices directly within the Home Assistant ecosystem, leveraging decentralized discovery and reputation systems, as well as buyer protection, forced tracked postage, with automatic payment on delivery confirmation, community moderation of listings, and community review of buyer disputes. no price changes or haggling after initial offer. cash on collection at seller discretion with a compulsory discount, to be agreed between seller and buyer (to account for saved postage costs). or tracked postage compulsory (at sellers cost). geolocated listings with map view, and simple calendar invites for collection arrangement. no fees for any listings or sales, ever.