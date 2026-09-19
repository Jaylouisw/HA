# HAGrid — UK Electrical Grid Map 🔌

Bring the UK electrical grid into your Home Assistant dashboard: real-time carbon intensity, the
generation mix, live DNO faults, and an interactive map of substations and power lines — powered by
the Carbon Intensity API and UK Power Networks open data.

## Quick start (manual install, current state)

HAGrid is not yet installable through HACS from this repository — the integration sits under
`HAGrid/custom_components/hagrid` rather than at the repository root, which is where HACS looks.

1. Copy `HAGrid/custom_components/hagrid` to `config/custom_components/hagrid` — the folder must be
   named exactly `hagrid`.
2. Copy `HAGrid/www/hagrid-map` to `config/www/hagrid-map`.
3. Restart Home Assistant.
4. **Settings** → **Devices & Services** → **Add Integration** → **HAGrid**, then enter your postcode
   or pick a region/DNO.

## What you get

- 📊 Carbon intensity (gCO2/kWh), carbon index, and a 48-hour forecast
- ⚡ Live generation mix — renewables vs fossil fuels
- 🗺️ An interactive map card: substations, 33kV/HV lines, embedded generation
- 🚨 Live faults and planned outages, with affected-customer counts

## Notes

- Every data source used is free and keyless (National Grid ESO's Carbon Intensity API, UKPN live
  faults, OpenStreetMap Overpass).
- See [`HAGrid/README.md`](../HAGrid/README.md) for the full documentation and the sensor list.
