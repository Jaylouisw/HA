# HAGrid - UK Electrical Grid Map 🔌

<p align="center">
  <img src="https://img.shields.io/badge/Home%20Assistant-2024.1+-blue?style=for-the-badge&logo=home-assistant" alt="Home Assistant">
  <img src="https://img.shields.io/badge/HACS-Custom-orange?style=for-the-badge" alt="HACS">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

**HAGrid** brings the UK electrical grid into Home Assistant! Monitor real-time carbon intensity, generation mix, live faults, and visualize your local grid infrastructure on an interactive map.

## ✨ Features

### 📊 Carbon Intelligence
- **Real-time carbon intensity** (gCO2/kWh) for your postcode/region
- **Carbon index** (very low → very high) with color coding
- **48-hour forecast** to help you plan energy usage
- **Best time recommendations** for low-carbon electricity

### ⚡ Generation Mix
- Live breakdown of electricity sources (wind, solar, gas, nuclear, etc.)
- Renewable vs fossil fuel percentages
- Historical trends and patterns

### 🗺️ Interactive Grid Map
- **Substations** - Grid, Primary, and Secondary
- **Power lines** - 33kV and HV overhead lines
- **Live faults** - Real-time power cuts and planned outages
- **Embedded generation** - Solar farms, wind turbines, batteries

### 🚨 Fault Monitoring
- Live power cuts in your DNO region
- Planned vs unplanned outages
- Affected customer counts
- Postcode-level detail

## 📦 Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots → **Custom repositories**
3. Add: `https://github.com/jaylouisw/HA`
4. Category: **Integration**
5. Search for "HAGrid" and install
6. Restart Home Assistant
7. Go to **Settings → Devices & Services → Add Integration → HAGrid**

### Manual Installation

1. Download the latest release
2. Extract to `custom_components/hagrid/`
3. Add the Lovelace card: copy `www/hagrid-map/` to your `www/` folder
4. Restart Home Assistant

## ⚙️ Configuration

### Setup
1. Enter your UK postcode (e.g., `SW1A 1AA`)
2. Select your electricity region (auto-detected from postcode)
3. Configure update intervals and display options

### Options
| Option | Default | Description |
|--------|---------|-------------|
| Update interval | 120s | How often to fetch new data |
| Show infrastructure | ✓ | Display substations and power lines |
| Show live faults | ✓ | Display active power cuts |
| Include forecast | ✓ | Fetch 48-hour carbon forecast |

## 🎴 Lovelace Card

Add the HAGrid map card to your dashboard:

```yaml
type: custom:hagrid-map-card
entity: sensor.hagrid_grid_map
title: UK Grid Map
height: 400px
show_generation_mix: true
show_infrastructure: true
show_faults: true
```

### Card Options
| Option | Type | Description |
|--------|------|-------------|
| `entity` | string | Map data sensor (required) |
| `title` | string | Card title |
| `height` | string | Map height (default: 400px) |
| `show_generation_mix` | boolean | Show generation bar chart |
| `show_infrastructure` | boolean | Show substations/lines on map |
| `show_faults` | boolean | Show live faults on map |
| `center` | [lat, lng] | Map center coordinates |
| `zoom` | number | Initial zoom level (default: 5) |

## 📡 Sensors

| Sensor | Description |
|--------|-------------|
| `sensor.hagrid_carbon_intensity` | Current carbon intensity (gCO2/kWh) |
| `sensor.hagrid_carbon_index` | Carbon index (very low to very high) |
| `sensor.hagrid_generation_mix` | Dominant fuel source |
| `sensor.hagrid_live_faults` | Number of active faults |
| `sensor.hagrid_carbon_forecast` | Trend direction |
| `sensor.hagrid_grid_map` | Full map data for Lovelace card |
| `sensor.hagrid_*_generation` | Individual fuel percentages |

## 🔧 Services

| Service | Description |
|---------|-------------|
| `hagrid.refresh_data` | Force refresh all data |
| `hagrid.refresh_infrastructure` | Refresh cached infrastructure |
| `hagrid.get_best_time` | Get optimal time for low-carbon usage |
| `hagrid.check_postcode` | Get data for any UK postcode |
| `hagrid.get_regional_comparison` | Compare all UK regions |

## 📊 Automations

### Notify When Carbon is Low
```yaml
automation:
  - alias: "Low Carbon Alert"
    trigger:
      - platform: state
        entity_id: sensor.hagrid_carbon_index
        to: "very low"
    action:
      - service: notify.mobile_app
        data:
          title: "🌿 Low Carbon Electricity!"
          message: "Great time to charge EVs or run appliances. Intensity: {{ states('sensor.hagrid_carbon_intensity') }} gCO2/kWh"
```

### Delay High-Power Devices
```yaml
automation:
  - alias: "Smart Charging"
    trigger:
      - platform: time
        at: input_datetime.ev_charge_time
    condition:
      - condition: state
        entity_id: sensor.hagrid_carbon_index
        state: "very high"
    action:
      - service: notify.mobile_app
        data:
          message: "Delaying EV charge - carbon intensity is high. Best time: {{ state_attr('sensor.hagrid_carbon_forecast', 'best_time') }}"
```

## 🗂️ Data Sources

HAGrid uses free, open APIs:

| Source | Data | License |
|--------|------|---------|
| [Carbon Intensity API](https://api.carbonintensity.org.uk/) | Carbon intensity, generation mix, forecasts | Open Government License |
| [UKPN Open Data](https://ukpowernetworks.opendatasoft.com/) | Substations, power lines, faults, embedded generation | CC BY 4.0 |

### Supported DNOs
- **UKPN** - UK Power Networks (London, East, South East)
- More DNOs coming soon (SSEN, ENWL, NPG, SPEN, NGED)

## 🛣️ Roadmap

- [ ] More DNO data sources (SSEN, ENWL, etc.)
- [ ] Energy Dashboard integration
- [ ] Smart meter data import
- [ ] P2P data sharing network
- [ ] Price signals (Octopus Agile, etc.)
- [ ] Grid frequency monitoring
- [ ] Custom region overlays

## 🤝 Contributing

Contributions welcome! See the main [HA repository](https://github.com/jaylouisw/HA) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  Made with ⚡ for the Home Assistant community
  <br>
  Part of the <a href="https://github.com/jaylouisw/HA">jaylouisw/HA</a> project
</p>
