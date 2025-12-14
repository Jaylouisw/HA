"""
Comprehensive Network Infrastructure Database for HAM Network.

Contains accurate geolocation data for:
- Internet Exchange Points (IXPs)
- Major Datacenters and Colocation Facilities
- Points of Presence (POPs)
- Telecom Exchanges (including BT exchanges in UK)
- Carrier Hotels
- Cable Landing Stations

Data sources:
- PeeringDB (https://www.peeringdb.com/)
- Euro-IX (https://www.euro-ix.net/)
- Packet Clearing House (https://www.pch.net/)
- Telegeography (https://www.telegeography.com/)
- Public facility databases
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FacilityLocation:
    """Geographic location of a network facility."""
    name: str
    city: str
    country: str
    country_code: str
    latitude: float
    longitude: float
    facility_type: str  # ixp, datacenter, pop, telecom_exchange, cable_landing, carrier_hotel
    operator: str | None = None
    address: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "city": self.city,
            "country": self.country,
            "country_code": self.country_code,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "facility_type": self.facility_type,
            "operator": self.operator,
            "address": self.address,
        }


# =============================================================================
# INTERNET EXCHANGE POINTS (IXPs) - Comprehensive Global List
# =============================================================================
# Format: "prefix": FacilityLocation(...)
# Coordinates are for the actual building/facility

IXP_PREFIXES: dict[str, FacilityLocation] = {
    # =========================================================================
    # EUROPE
    # =========================================================================
    
    # DE-CIX Frankfurt (World's largest IXP by traffic)
    "80.81.192.0/22": FacilityLocation("DE-CIX Frankfurt", "Frankfurt", "Germany", "DE", 50.1109, 8.6821, "ixp", "DE-CIX", "Hanauer Landstraße 298"),
    "80.81.196.0/22": FacilityLocation("DE-CIX Frankfurt", "Frankfurt", "Germany", "DE", 50.1109, 8.6821, "ixp", "DE-CIX"),
    "2001:7f8::/32": FacilityLocation("DE-CIX Frankfurt", "Frankfurt", "Germany", "DE", 50.1109, 8.6821, "ixp", "DE-CIX"),
    
    # DE-CIX Munich
    "80.81.200.0/23": FacilityLocation("DE-CIX Munich", "Munich", "Germany", "DE", 48.1351, 11.5820, "ixp", "DE-CIX"),
    
    # DE-CIX Hamburg
    "80.81.202.0/23": FacilityLocation("DE-CIX Hamburg", "Hamburg", "Germany", "DE", 53.5511, 9.9937, "ixp", "DE-CIX"),
    
    # DE-CIX Dusseldorf
    "80.81.204.0/23": FacilityLocation("DE-CIX Dusseldorf", "Dusseldorf", "Germany", "DE", 51.2277, 6.7735, "ixp", "DE-CIX"),
    
    # AMS-IX Amsterdam (One of the largest IXPs)
    "80.249.208.0/21": FacilityLocation("AMS-IX", "Amsterdam", "Netherlands", "NL", 52.3034, 4.9390, "ixp", "AMS-IX", "Frederiksplein 42"),
    "80.249.208.0/22": FacilityLocation("AMS-IX", "Amsterdam", "Netherlands", "NL", 52.3034, 4.9390, "ixp", "AMS-IX"),
    "80.249.212.0/22": FacilityLocation("AMS-IX", "Amsterdam", "Netherlands", "NL", 52.3034, 4.9390, "ixp", "AMS-IX"),
    "2001:7f8:1::/48": FacilityLocation("AMS-IX", "Amsterdam", "Netherlands", "NL", 52.3034, 4.9390, "ixp", "AMS-IX"),
    "2001:7f8:1::/64": FacilityLocation("AMS-IX", "Amsterdam", "Netherlands", "NL", 52.3034, 4.9390, "ixp", "AMS-IX"),
    
    # LINX London (London Internet Exchange)
    "195.66.224.0/21": FacilityLocation("LINX LON1", "London", "United Kingdom", "GB", 51.5194, -0.0175, "ixp", "LINX", "Harbour Exchange"),
    "195.66.224.0/22": FacilityLocation("LINX LON1", "London", "United Kingdom", "GB", 51.5194, -0.0175, "ixp", "LINX"),
    "195.66.228.0/22": FacilityLocation("LINX LON1", "London", "United Kingdom", "GB", 51.5194, -0.0175, "ixp", "LINX"),
    "195.66.232.0/22": FacilityLocation("LINX LON2", "Slough", "United Kingdom", "GB", 51.5074, -0.5950, "ixp", "LINX", "Equinix LD4/LD5"),
    "2001:7f8:4::/48": FacilityLocation("LINX LON1", "London", "United Kingdom", "GB", 51.5194, -0.0175, "ixp", "LINX"),
    "2001:7f8:4::/64": FacilityLocation("LINX LON1", "London", "United Kingdom", "GB", 51.5194, -0.0175, "ixp", "LINX"),
    "2001:7f8:4::1/64": FacilityLocation("LINX LON2", "Slough", "United Kingdom", "GB", 51.5074, -0.5950, "ixp", "LINX"),
    
    # LINX Manchester
    "195.66.236.0/22": FacilityLocation("LINX Manchester", "Manchester", "United Kingdom", "GB", 53.4808, -2.2426, "ixp", "LINX"),
    
    # LONAP (London Access Point)
    "5.57.80.0/22": FacilityLocation("LONAP", "London", "United Kingdom", "GB", 51.5194, -0.0175, "ixp", "LONAP"),
    "2001:7f8:17::/48": FacilityLocation("LONAP", "London", "United Kingdom", "GB", 51.5194, -0.0175, "ixp", "LONAP"),
    
    # IXMANC (IX Manchester)
    "185.1.68.0/24": FacilityLocation("IXManchester", "Manchester", "United Kingdom", "GB", 53.4723, -2.2935, "ixp"),
    
    # France-IX Paris
    "37.49.236.0/22": FacilityLocation("France-IX Paris", "Paris", "France", "FR", 48.9241, 2.3600, "ixp", "France-IX", "Interxion PAR5"),
    "2001:7f8:54::/48": FacilityLocation("France-IX Paris", "Paris", "France", "FR", 48.9241, 2.3600, "ixp", "France-IX"),
    
    # France-IX Marseille
    "37.49.232.0/22": FacilityLocation("France-IX Marseille", "Marseille", "France", "FR", 43.2965, 5.3698, "ixp", "France-IX"),
    
    # ESPANIX Madrid
    "193.149.1.0/24": FacilityLocation("ESPANIX", "Madrid", "Spain", "ES", 40.4168, -3.7038, "ixp", "ESPANIX"),
    "2001:7f8:f::/48": FacilityLocation("ESPANIX", "Madrid", "Spain", "ES", 40.4168, -3.7038, "ixp", "ESPANIX"),
    
    # MIX Milan
    "217.29.66.0/23": FacilityLocation("MIX Milan", "Milan", "Italy", "IT", 45.4773, 9.1815, "ixp", "MIX"),
    "2001:7f8:b::/48": FacilityLocation("MIX Milan", "Milan", "Italy", "IT", 45.4773, 9.1815, "ixp", "MIX"),
    
    # NAMEX Rome
    "217.29.72.0/24": FacilityLocation("NAMEX Rome", "Rome", "Italy", "IT", 41.9028, 12.4964, "ixp", "NAMEX"),
    
    # VIX Vienna
    "193.203.0.0/23": FacilityLocation("VIX Vienna", "Vienna", "Austria", "AT", 48.2082, 16.3738, "ixp", "VIX"),
    "2001:7f8:30::/48": FacilityLocation("VIX Vienna", "Vienna", "Austria", "AT", 48.2082, 16.3738, "ixp", "VIX"),
    
    # SwissIX Zurich
    "91.206.52.0/23": FacilityLocation("SwissIX", "Zurich", "Switzerland", "CH", 47.3769, 8.5417, "ixp", "SwissIX"),
    "2001:7f8:24::/48": FacilityLocation("SwissIX", "Zurich", "Switzerland", "CH", 47.3769, 8.5417, "ixp", "SwissIX"),
    
    # NIX.CZ Prague
    "91.210.16.0/22": FacilityLocation("NIX.CZ", "Prague", "Czech Republic", "CZ", 50.0755, 14.4378, "ixp", "NIX.CZ"),
    "2001:7f8:14::/48": FacilityLocation("NIX.CZ", "Prague", "Czech Republic", "CZ", 50.0755, 14.4378, "ixp", "NIX.CZ"),
    
    # PLIX Warsaw
    "195.182.218.0/23": FacilityLocation("PLIX", "Warsaw", "Poland", "PL", 52.2297, 21.0122, "ixp", "PLIX"),
    
    # Netnod Stockholm
    "194.68.128.0/22": FacilityLocation("Netnod Stockholm", "Stockholm", "Sweden", "SE", 59.3293, 18.0686, "ixp", "Netnod"),
    "2001:7f8:d::/48": FacilityLocation("Netnod Stockholm", "Stockholm", "Sweden", "SE", 59.3293, 18.0686, "ixp", "Netnod"),
    
    # FICIX Helsinki
    "193.110.224.0/23": FacilityLocation("FICIX", "Helsinki", "Finland", "FI", 60.1699, 24.9384, "ixp", "FICIX"),
    
    # MSK-IX Moscow
    "195.208.208.0/21": FacilityLocation("MSK-IX", "Moscow", "Russia", "RU", 55.7558, 37.6173, "ixp", "MSK-IX"),
    "2001:7f8:20::/48": FacilityLocation("MSK-IX", "Moscow", "Russia", "RU", 55.7558, 37.6173, "ixp", "MSK-IX"),
    
    # NL-ix Amsterdam
    "193.239.116.0/22": FacilityLocation("NL-ix", "Amsterdam", "Netherlands", "NL", 52.3547, 4.8339, "ixp", "NL-ix"),
    "2001:7f8:13::/48": FacilityLocation("NL-ix", "Amsterdam", "Netherlands", "NL", 52.3547, 4.8339, "ixp", "NL-ix"),
    
    # BCIX Berlin
    "193.178.185.0/24": FacilityLocation("BCIX", "Berlin", "Germany", "DE", 52.5200, 13.4050, "ixp", "BCIX"),
    "2001:7f8:19::/48": FacilityLocation("BCIX", "Berlin", "Germany", "DE", 52.5200, 13.4050, "ixp", "BCIX"),
    
    # =========================================================================
    # NORTH AMERICA
    # =========================================================================
    
    # Equinix IX Ashburn (Major US East Coast hub)
    "206.126.236.0/22": FacilityLocation("Equinix Ashburn", "Ashburn", "United States", "US", 39.0438, -77.4874, "ixp", "Equinix", "21715 Filigree Ct"),
    "2001:504:0:2::/64": FacilityLocation("Equinix Ashburn", "Ashburn", "United States", "US", 39.0438, -77.4874, "ixp", "Equinix"),
    
    # Equinix IX San Jose
    "198.32.160.0/21": FacilityLocation("Equinix San Jose", "San Jose", "United States", "US", 37.3873, -121.9610, "ixp", "Equinix", "11 Great Oaks Blvd"),
    
    # Equinix IX Chicago
    "206.223.116.0/22": FacilityLocation("Equinix Chicago", "Chicago", "United States", "US", 41.8500, -87.6594, "ixp", "Equinix"),
    
    # Equinix IX Dallas
    "206.223.122.0/23": FacilityLocation("Equinix Dallas", "Dallas", "United States", "US", 32.8968, -96.8250, "ixp", "Equinix"),
    
    # Equinix IX Los Angeles
    "206.223.118.0/23": FacilityLocation("Equinix Los Angeles", "Los Angeles", "United States", "US", 34.0549, -118.2426, "ixp", "Equinix"),
    
    # DE-CIX New York
    "206.82.104.0/22": FacilityLocation("DE-CIX New York", "New York", "United States", "US", 40.7392, -74.0031, "ixp", "DE-CIX"),
    
    # SIX Seattle
    "206.81.80.0/22": FacilityLocation("SIX Seattle", "Seattle", "United States", "US", 47.6131, -122.3414, "ixp", "SIX", "2001 Sixth Avenue"),
    "2001:504:16::/64": FacilityLocation("SIX Seattle", "Seattle", "United States", "US", 47.6131, -122.3414, "ixp", "SIX"),
    
    # NYIIX New York
    "198.32.118.0/24": FacilityLocation("NYIIX", "New York", "United States", "US", 40.7282, -73.9942, "ixp", "Telehouse"),
    "2001:504:1::/64": FacilityLocation("NYIIX", "New York", "United States", "US", 40.7282, -73.9942, "ixp", "Telehouse"),
    
    # Any2 Los Angeles
    "206.72.210.0/23": FacilityLocation("Any2 Exchange", "Los Angeles", "United States", "US", 34.0549, -118.2426, "ixp", "CoreSite"),
    "185.1.0.0/22": FacilityLocation("Any2 Exchange", "Los Angeles", "United States", "US", 34.0549, -118.2426, "ixp", "CoreSite"),
    
    # MICE Minneapolis
    "206.53.139.0/24": FacilityLocation("MICE", "Minneapolis", "United States", "US", 44.9778, -93.2650, "ixp", "MICE"),
    
    # TorIX Toronto
    "206.108.34.0/24": FacilityLocation("TorIX", "Toronto", "Canada", "CA", 43.6532, -79.3832, "ixp", "TorIX"),
    "2001:504:1a::/64": FacilityLocation("TorIX", "Toronto", "Canada", "CA", 43.6532, -79.3832, "ixp", "TorIX"),
    
    # QIX Montreal
    "198.179.19.0/24": FacilityLocation("QIX", "Montreal", "Canada", "CA", 45.5017, -73.5673, "ixp", "QIX"),
    
    # VANIX Vancouver
    "206.41.110.0/24": FacilityLocation("VANIX", "Vancouver", "Canada", "CA", 49.2827, -123.1207, "ixp", "VANIX"),
    
    # MegaIX Miami
    "206.197.184.0/24": FacilityLocation("MegaIX Miami", "Miami", "United States", "US", 25.7854, -80.1870, "ixp", "Mega-IX"),
    
    # =========================================================================
    # ASIA-PACIFIC
    # =========================================================================
    
    # JPNAP Tokyo
    "210.171.224.0/23": FacilityLocation("JPNAP Tokyo", "Tokyo", "Japan", "JP", 35.6595, 139.7004, "ixp", "JPNAP"),
    "2001:7fa:7::/48": FacilityLocation("JPNAP Tokyo", "Tokyo", "Japan", "JP", 35.6595, 139.7004, "ixp", "JPNAP"),
    
    # JPIX Tokyo
    "210.173.176.0/24": FacilityLocation("JPIX Tokyo", "Tokyo", "Japan", "JP", 35.6762, 139.6503, "ixp", "JPIX"),
    
    # BBIX Tokyo
    "103.2.248.0/22": FacilityLocation("BBIX Tokyo", "Tokyo", "Japan", "JP", 35.6869, 139.7544, "ixp", "SoftBank"),
    
    # Equinix Singapore
    "103.16.102.0/23": FacilityLocation("Equinix Singapore", "Singapore", "Singapore", "SG", 1.3200, 103.8200, "ixp", "Equinix"),
    
    # SGIX Singapore
    "103.52.68.0/22": FacilityLocation("SGIX", "Singapore", "Singapore", "SG", 1.2931, 103.8558, "ixp", "SGIX"),
    
    # HKIX Hong Kong
    "202.40.161.0/24": FacilityLocation("HKIX", "Hong Kong", "Hong Kong", "HK", 22.3526, 114.1231, "ixp", "HKIX"),
    "2001:7fa:0:1::/64": FacilityLocation("HKIX", "Hong Kong", "Hong Kong", "HK", 22.3526, 114.1231, "ixp", "HKIX"),
    
    # Equinix Hong Kong
    "103.41.12.0/22": FacilityLocation("Equinix Hong Kong", "Hong Kong", "Hong Kong", "HK", 22.3580, 114.1286, "ixp", "Equinix"),
    
    # KINX Seoul
    "121.189.0.0/24": FacilityLocation("KINX", "Seoul", "South Korea", "KR", 37.5665, 126.9780, "ixp", "KINX"),
    
    # TWIX Taipei
    "203.73.24.0/23": FacilityLocation("TWIX", "Taipei", "Taiwan", "TW", 25.0330, 121.5654, "ixp", "TWIX"),
    
    # CNIX Beijing
    "202.97.0.0/19": FacilityLocation("CNIX", "Beijing", "China", "CN", 39.9042, 116.4074, "ixp", "China Telecom"),
    
    # IX Australia Sydney
    "218.100.52.0/22": FacilityLocation("IX Australia Sydney", "Sydney", "Australia", "AU", -33.8651, 151.2099, "ixp", "IX Australia"),
    "2001:7fa:11::/48": FacilityLocation("IX Australia Sydney", "Sydney", "Australia", "AU", -33.8651, 151.2099, "ixp", "IX Australia"),
    
    # IX Australia Melbourne
    "218.100.56.0/22": FacilityLocation("IX Australia Melbourne", "Melbourne", "Australia", "AU", -37.8100, 144.9628, "ixp", "IX Australia"),
    
    # MegaIX Sydney
    "103.26.68.0/22": FacilityLocation("MegaIX Sydney", "Sydney", "Australia", "AU", -33.8688, 151.2093, "ixp", "Megaport"),
    
    # NZIX Auckland
    "192.203.154.0/24": FacilityLocation("NZIX", "Auckland", "New Zealand", "NZ", -36.8509, 174.7645, "ixp", "NZIX"),
    
    # =========================================================================
    # LATIN AMERICA
    # =========================================================================
    
    # IX.br São Paulo (PTT Metro)
    "187.16.192.0/21": FacilityLocation("IX.br São Paulo", "São Paulo", "Brazil", "BR", -23.5505, -46.6333, "ixp", "NIC.br"),
    "2001:12f8::/32": FacilityLocation("IX.br São Paulo", "São Paulo", "Brazil", "BR", -23.5505, -46.6333, "ixp", "NIC.br"),
    
    # IX.br Rio de Janeiro
    "187.16.200.0/21": FacilityLocation("IX.br Rio de Janeiro", "Rio de Janeiro", "Brazil", "BR", -22.9068, -43.1729, "ixp", "NIC.br"),
    
    # CABASE Buenos Aires
    "200.68.240.0/22": FacilityLocation("CABASE", "Buenos Aires", "Argentina", "AR", -34.6037, -58.3816, "ixp", "CABASE"),
    
    # NAP Chile Santiago
    "200.1.121.0/24": FacilityLocation("NAP Chile", "Santiago", "Chile", "CL", -33.4489, -70.6693, "ixp", "NAP Chile"),
    
    # =========================================================================
    # MIDDLE EAST & AFRICA
    # =========================================================================
    
    # UAE-IX Dubai
    "185.1.60.0/22": FacilityLocation("UAE-IX", "Dubai", "United Arab Emirates", "AE", 25.2048, 55.2708, "ixp", "UAE-IX"),
    
    # DE-CIX Istanbul
    "185.1.76.0/22": FacilityLocation("DE-CIX Istanbul", "Istanbul", "Turkey", "TR", 41.0082, 28.9784, "ixp", "DE-CIX"),
    
    # NAPAfrica Johannesburg
    "196.60.8.0/22": FacilityLocation("NAPAfrica JHB", "Johannesburg", "South Africa", "ZA", -26.2041, 28.0473, "ixp", "NAPAfrica"),
    
    # KIXP Nairobi
    "196.6.220.0/22": FacilityLocation("KIXP", "Nairobi", "Kenya", "KE", -1.2921, 36.8219, "ixp", "KIXP"),
}


# =============================================================================
# MAJOR DATACENTERS WITH ACCURATE COORDINATES
# =============================================================================

DATACENTER_LOCATIONS: dict[str, FacilityLocation] = {
    # =========================================================================
    # EQUINIX DATACENTERS (Global)
    # =========================================================================
    
    # London
    "equinix_ld4": FacilityLocation("Equinix LD4", "Slough", "United Kingdom", "GB", 51.5074, -0.5897, "datacenter", "Equinix", "8 Buckingham Ave"),
    "equinix_ld5": FacilityLocation("Equinix LD5", "Slough", "United Kingdom", "GB", 51.5122, -0.5836, "datacenter", "Equinix", "6 Buckingham Ave"),
    "equinix_ld6": FacilityLocation("Equinix LD6", "Slough", "United Kingdom", "GB", 51.5074, -0.5950, "datacenter", "Equinix"),
    "equinix_ld8": FacilityLocation("Equinix LD8", "London", "United Kingdom", "GB", 51.5154, -0.0094, "datacenter", "Equinix", "Harbour Exchange"),
    
    # Amsterdam
    "equinix_am1": FacilityLocation("Equinix AM1", "Amsterdam", "Netherlands", "NL", 52.3037, 4.9389, "datacenter", "Equinix", "Luttenbergweg 4"),
    "equinix_am3": FacilityLocation("Equinix AM3", "Amsterdam", "Netherlands", "NL", 52.2868, 4.9525, "datacenter", "Equinix"),
    "equinix_am5": FacilityLocation("Equinix AM5", "Amsterdam", "Netherlands", "NL", 52.3034, 4.9415, "datacenter", "Equinix"),
    "equinix_am7": FacilityLocation("Equinix AM7", "Amsterdam", "Netherlands", "NL", 52.3407, 4.8893, "datacenter", "Equinix"),
    
    # Frankfurt
    "equinix_fr2": FacilityLocation("Equinix FR2", "Frankfurt", "Germany", "DE", 50.1021, 8.7086, "datacenter", "Equinix"),
    "equinix_fr4": FacilityLocation("Equinix FR4", "Frankfurt", "Germany", "DE", 50.1149, 8.6701, "datacenter", "Equinix"),
    "equinix_fr5": FacilityLocation("Equinix FR5", "Frankfurt", "Germany", "DE", 50.0866, 8.6333, "datacenter", "Equinix"),
    
    # US East
    "equinix_dc1": FacilityLocation("Equinix DC1", "Ashburn", "United States", "US", 39.0438, -77.4874, "datacenter", "Equinix", "21715 Filigree Ct"),
    "equinix_dc2": FacilityLocation("Equinix DC2", "Ashburn", "United States", "US", 39.0475, -77.4826, "datacenter", "Equinix"),
    "equinix_dc6": FacilityLocation("Equinix DC6", "Ashburn", "United States", "US", 39.0350, -77.4630, "datacenter", "Equinix"),
    "equinix_ny1": FacilityLocation("Equinix NY1", "Secaucus", "United States", "US", 40.7785, -74.0752, "datacenter", "Equinix"),
    "equinix_ny4": FacilityLocation("Equinix NY4", "Secaucus", "United States", "US", 40.7852, -74.0644, "datacenter", "Equinix"),
    "equinix_ny5": FacilityLocation("Equinix NY5", "Secaucus", "United States", "US", 40.7830, -74.0592, "datacenter", "Equinix"),
    
    # US West
    "equinix_sv1": FacilityLocation("Equinix SV1", "San Jose", "United States", "US", 37.3873, -121.9610, "datacenter", "Equinix"),
    "equinix_sv5": FacilityLocation("Equinix SV5", "San Jose", "United States", "US", 37.3909, -121.9633, "datacenter", "Equinix"),
    "equinix_la1": FacilityLocation("Equinix LA1", "Los Angeles", "United States", "US", 34.0549, -118.2426, "datacenter", "Equinix"),
    "equinix_se2": FacilityLocation("Equinix SE2", "Seattle", "United States", "US", 47.6131, -122.3414, "datacenter", "Equinix"),
    
    # =========================================================================
    # INTERXION DATACENTERS (Europe)
    # =========================================================================
    
    "interxion_lon1": FacilityLocation("Interxion LON1", "London", "United Kingdom", "GB", 51.5227, -0.0712, "datacenter", "Interxion"),
    "interxion_lon2": FacilityLocation("Interxion LON2", "London", "United Kingdom", "GB", 51.5181, -0.0176, "datacenter", "Interxion"),
    "interxion_ams1": FacilityLocation("Interxion AMS1", "Amsterdam", "Netherlands", "NL", 52.3380, 4.8899, "datacenter", "Interxion"),
    "interxion_fra1": FacilityLocation("Interxion FRA1", "Frankfurt", "Germany", "DE", 50.1109, 8.6821, "datacenter", "Interxion"),
    "interxion_par5": FacilityLocation("Interxion PAR5", "Paris", "France", "FR", 48.9241, 2.3600, "datacenter", "Interxion"),
    
    # =========================================================================
    # TELEHOUSE DATACENTERS
    # =========================================================================
    
    "telehouse_london_east": FacilityLocation("Telehouse East", "London", "United Kingdom", "GB", 51.5118, 0.0032, "datacenter", "Telehouse", "Coriander Ave"),
    "telehouse_london_north": FacilityLocation("Telehouse North", "London", "United Kingdom", "GB", 51.5196, -0.0081, "datacenter", "Telehouse"),
    "telehouse_paris": FacilityLocation("Telehouse Paris Voltaire", "Paris", "France", "FR", 48.8621, 2.3958, "datacenter", "Telehouse"),
    
    # =========================================================================
    # DIGITAL REALTY DATACENTERS
    # =========================================================================
    
    "digital_realty_ams": FacilityLocation("Digital Realty Amsterdam", "Amsterdam", "Netherlands", "NL", 52.3034, 4.9390, "datacenter", "Digital Realty"),
    "digital_realty_lon": FacilityLocation("Digital Realty London", "London", "United Kingdom", "GB", 51.5194, -0.0175, "datacenter", "Digital Realty"),
    
    # =========================================================================
    # CORESITE DATACENTERS (US)
    # =========================================================================
    
    "coresite_la1": FacilityLocation("CoreSite LA1", "Los Angeles", "United States", "US", 34.0549, -118.2426, "datacenter", "CoreSite", "624 S Grand Ave"),
    "coresite_sv1": FacilityLocation("CoreSite SV1", "Santa Clara", "United States", "US", 37.3861, -121.9682, "datacenter", "CoreSite"),
    "coresite_dc1": FacilityLocation("CoreSite DC1", "Reston", "United States", "US", 38.9495, -77.3467, "datacenter", "CoreSite"),
}


# =============================================================================
# UK TELECOM EXCHANGES (BT and Others)
# =============================================================================
# BT's 21CN network uses major telephone exchanges as POPs

UK_TELECOM_EXCHANGES: dict[str, FacilityLocation] = {
    # Major BT Trunk Exchanges
    "bt_london_city": FacilityLocation("BT London City", "London", "United Kingdom", "GB", 51.5139, -0.0884, "telecom_exchange", "BT", "Monument"),
    "bt_london_bishops": FacilityLocation("BT Bishopsgate", "London", "United Kingdom", "GB", 51.5177, -0.0807, "telecom_exchange", "BT"),
    "bt_london_holborn": FacilityLocation("BT Holborn", "London", "United Kingdom", "GB", 51.5177, -0.1180, "telecom_exchange", "BT"),
    "bt_london_victoria": FacilityLocation("BT Victoria", "London", "United Kingdom", "GB", 51.4966, -0.1448, "telecom_exchange", "BT"),
    "bt_london_kensington": FacilityLocation("BT Kensington", "London", "United Kingdom", "GB", 51.4971, -0.1780, "telecom_exchange", "BT"),
    "bt_london_docklands": FacilityLocation("BT Docklands", "London", "United Kingdom", "GB", 51.5054, 0.0235, "telecom_exchange", "BT"),
    
    # BT Regional Hub Exchanges
    "bt_birmingham": FacilityLocation("BT Birmingham", "Birmingham", "United Kingdom", "GB", 52.4797, -1.9026, "telecom_exchange", "BT", "Newhall St"),
    "bt_manchester": FacilityLocation("BT Manchester", "Manchester", "United Kingdom", "GB", 53.4808, -2.2426, "telecom_exchange", "BT", "Aytoun St"),
    "bt_leeds": FacilityLocation("BT Leeds", "Leeds", "United Kingdom", "GB", 53.8008, -1.5491, "telecom_exchange", "BT"),
    "bt_glasgow": FacilityLocation("BT Glasgow", "Glasgow", "United Kingdom", "GB", 55.8642, -4.2518, "telecom_exchange", "BT"),
    "bt_edinburgh": FacilityLocation("BT Edinburgh", "Edinburgh", "United Kingdom", "GB", 55.9533, -3.1883, "telecom_exchange", "BT"),
    "bt_bristol": FacilityLocation("BT Bristol", "Bristol", "United Kingdom", "GB", 51.4545, -2.5879, "telecom_exchange", "BT"),
    "bt_liverpool": FacilityLocation("BT Liverpool", "Liverpool", "United Kingdom", "GB", 53.4084, -2.9916, "telecom_exchange", "BT"),
    "bt_newcastle": FacilityLocation("BT Newcastle", "Newcastle", "United Kingdom", "GB", 54.9783, -1.6178, "telecom_exchange", "BT"),
    "bt_sheffield": FacilityLocation("BT Sheffield", "Sheffield", "United Kingdom", "GB", 53.3811, -1.4701, "telecom_exchange", "BT"),
    "bt_cardiff": FacilityLocation("BT Cardiff", "Cardiff", "United Kingdom", "GB", 51.4816, -3.1791, "telecom_exchange", "BT"),
    "bt_belfast": FacilityLocation("BT Belfast", "Belfast", "United Kingdom", "GB", 54.5973, -5.9301, "telecom_exchange", "BT"),
    "bt_reading": FacilityLocation("BT Reading", "Reading", "United Kingdom", "GB", 51.4551, -0.9787, "telecom_exchange", "BT"),
    "bt_slough": FacilityLocation("BT Slough", "Slough", "United Kingdom", "GB", 51.5105, -0.5950, "telecom_exchange", "BT"),
    "bt_nottingham": FacilityLocation("BT Nottingham", "Nottingham", "United Kingdom", "GB", 52.9548, -1.1581, "telecom_exchange", "BT"),
    "bt_southampton": FacilityLocation("BT Southampton", "Southampton", "United Kingdom", "GB", 50.9097, -1.4044, "telecom_exchange", "BT"),
    "bt_cambridge": FacilityLocation("BT Cambridge", "Cambridge", "United Kingdom", "GB", 52.2053, 0.1218, "telecom_exchange", "BT"),
    "bt_brighton": FacilityLocation("BT Brighton", "Brighton", "United Kingdom", "GB", 50.8225, -0.1372, "telecom_exchange", "BT"),
    
    # BT Tower (Major hub)
    "bt_tower": FacilityLocation("BT Tower", "London", "United Kingdom", "GB", 51.5215, -0.1389, "telecom_exchange", "BT", "60 Cleveland St"),
    
    # Virgin Media / Liberty Global exchanges
    "virgin_london": FacilityLocation("Virgin Media London", "London", "United Kingdom", "GB", 51.5124, -0.0911, "telecom_exchange", "Virgin Media"),
    "virgin_manchester": FacilityLocation("Virgin Media Manchester", "Manchester", "United Kingdom", "GB", 53.4750, -2.2530, "telecom_exchange", "Virgin Media"),
    "virgin_birmingham": FacilityLocation("Virgin Media Birmingham", "Birmingham", "United Kingdom", "GB", 52.4862, -1.8904, "telecom_exchange", "Virgin Media"),
    
    # TalkTalk exchanges
    "talktalk_london": FacilityLocation("TalkTalk London", "London", "United Kingdom", "GB", 51.4915, -0.0966, "telecom_exchange", "TalkTalk"),
    
    # Sky/NOW exchanges (Brentford)
    "sky_osterley": FacilityLocation("Sky Osterley", "Osterley", "United Kingdom", "GB", 51.4787, -0.3505, "telecom_exchange", "Sky"),
}


# =============================================================================
# CABLE LANDING STATIONS
# =============================================================================

CABLE_LANDING_STATIONS: dict[str, FacilityLocation] = {
    # UK
    "porthcurno": FacilityLocation("Porthcurno CLS", "Porthcurno", "United Kingdom", "GB", 50.0427, -5.6581, "cable_landing", "Various"),
    "bude": FacilityLocation("Bude CLS", "Bude", "United Kingdom", "GB", 50.8309, -4.5439, "cable_landing", "Various"),
    "whitesands": FacilityLocation("Whitesands CLS", "Whitesands Bay", "United Kingdom", "GB", 51.8704, -5.2960, "cable_landing", "Various"),
    "highbridge": FacilityLocation("Highbridge CLS", "Highbridge", "United Kingdom", "GB", 51.2195, -2.9734, "cable_landing", "Various"),
    "lowestoft": FacilityLocation("Lowestoft CLS", "Lowestoft", "United Kingdom", "GB", 52.4716, 1.7527, "cable_landing", "Various"),
    
    # US East Coast
    "long_island": FacilityLocation("Long Island CLS", "Long Island", "United States", "US", 40.8304, -72.7772, "cable_landing", "Various"),
    "wall_township": FacilityLocation("Wall Township CLS", "Wall Township", "United States", "US", 40.1659, -74.0653, "cable_landing", "Telia"),
    "virginia_beach": FacilityLocation("Virginia Beach CLS", "Virginia Beach", "United States", "US", 36.8506, -75.9779, "cable_landing", "Various"),
    "miami_cls": FacilityLocation("Miami CLS", "Miami", "United States", "US", 25.7617, -80.1918, "cable_landing", "Various"),
    
    # US West Coast
    "hillsboro": FacilityLocation("Hillsboro CLS", "Hillsboro", "United States", "US", 45.5231, -122.9898, "cable_landing", "Google"),
    "morro_bay": FacilityLocation("Morro Bay CLS", "Morro Bay", "United States", "US", 35.3658, -120.8499, "cable_landing", "Various"),
    "hermosa_beach": FacilityLocation("Hermosa Beach CLS", "Hermosa Beach", "United States", "US", 33.8622, -118.3995, "cable_landing", "Various"),
    
    # Europe
    "marseille_cls": FacilityLocation("Marseille CLS", "Marseille", "France", "FR", 43.2965, 5.3698, "cable_landing", "Various"),
    "lisbon_cls": FacilityLocation("Lisbon CLS", "Carcavelos", "Portugal", "PT", 38.6776, -9.3354, "cable_landing", "Various"),
    
    # Asia
    "singapore_cls": FacilityLocation("Singapore CLS", "Singapore", "Singapore", "SG", 1.3521, 103.8198, "cable_landing", "Various"),
    "hong_kong_cls": FacilityLocation("Hong Kong CLS", "Chung Hom Kok", "Hong Kong", "HK", 22.2141, 114.2081, "cable_landing", "Various"),
    "tokyo_cls": FacilityLocation("Tokyo CLS", "Chiba", "Japan", "JP", 35.6072, 140.1062, "cable_landing", "Various"),
}


# =============================================================================
# POINTS OF PRESENCE (PoPs) - Major Network Provider POPs
# =============================================================================

POPS: dict[str, FacilityLocation] = {
    # Cloudflare POPs (major ones)
    "cloudflare_lon": FacilityLocation("Cloudflare London", "London", "United Kingdom", "GB", 51.5194, -0.0175, "pop", "Cloudflare"),
    "cloudflare_ams": FacilityLocation("Cloudflare Amsterdam", "Amsterdam", "Netherlands", "NL", 52.3034, 4.9390, "pop", "Cloudflare"),
    "cloudflare_fra": FacilityLocation("Cloudflare Frankfurt", "Frankfurt", "Germany", "DE", 50.1109, 8.6821, "pop", "Cloudflare"),
    "cloudflare_par": FacilityLocation("Cloudflare Paris", "Paris", "France", "FR", 48.8566, 2.3522, "pop", "Cloudflare"),
    "cloudflare_nyc": FacilityLocation("Cloudflare New York", "New York", "United States", "US", 40.7128, -74.0060, "pop", "Cloudflare"),
    "cloudflare_sfo": FacilityLocation("Cloudflare San Francisco", "San Francisco", "United States", "US", 37.7749, -122.4194, "pop", "Cloudflare"),
    "cloudflare_lax": FacilityLocation("Cloudflare Los Angeles", "Los Angeles", "United States", "US", 34.0522, -118.2437, "pop", "Cloudflare"),
    "cloudflare_sin": FacilityLocation("Cloudflare Singapore", "Singapore", "Singapore", "SG", 1.3521, 103.8198, "pop", "Cloudflare"),
    "cloudflare_hkg": FacilityLocation("Cloudflare Hong Kong", "Hong Kong", "Hong Kong", "HK", 22.3193, 114.1694, "pop", "Cloudflare"),
    "cloudflare_tyo": FacilityLocation("Cloudflare Tokyo", "Tokyo", "Japan", "JP", 35.6762, 139.6503, "pop", "Cloudflare"),
    
    # Akamai POPs
    "akamai_lon": FacilityLocation("Akamai London", "London", "United Kingdom", "GB", 51.5074, -0.1278, "pop", "Akamai"),
    "akamai_ams": FacilityLocation("Akamai Amsterdam", "Amsterdam", "Netherlands", "NL", 52.3676, 4.9041, "pop", "Akamai"),
    "akamai_ash": FacilityLocation("Akamai Ashburn", "Ashburn", "United States", "US", 39.0438, -77.4874, "pop", "Akamai"),
    
    # Google Edge POPs (GGC)
    "google_lon": FacilityLocation("Google London", "London", "United Kingdom", "GB", 51.5032, -0.0141, "pop", "Google"),
    "google_ams": FacilityLocation("Google Amsterdam", "Amsterdam", "Netherlands", "NL", 52.3579, 4.8686, "pop", "Google"),
    "google_fra": FacilityLocation("Google Frankfurt", "Frankfurt", "Germany", "DE", 50.1109, 8.6821, "pop", "Google"),
    
    # Netflix Open Connect POPs
    "netflix_lon": FacilityLocation("Netflix London", "London", "United Kingdom", "GB", 51.5194, -0.0175, "pop", "Netflix"),
    "netflix_ams": FacilityLocation("Netflix Amsterdam", "Amsterdam", "Netherlands", "NL", 52.3034, 4.9390, "pop", "Netflix"),
}


# =============================================================================
# CARRIER HOTELS (Multi-tenant neutral facilities)
# =============================================================================

CARRIER_HOTELS: dict[str, FacilityLocation] = {
    # London
    "ld_harbex": FacilityLocation("Harbour Exchange", "London", "United Kingdom", "GB", 51.5194, -0.0175, "carrier_hotel", "Various"),
    "ld_telehouse": FacilityLocation("Telehouse Docklands", "London", "United Kingdom", "GB", 51.5118, 0.0032, "carrier_hotel", "Telehouse"),
    "ld_sovereign": FacilityLocation("Sovereign House", "London", "United Kingdom", "GB", 51.5200, -0.0800, "carrier_hotel", "Various"),
    
    # New York
    "ny_111eighth": FacilityLocation("111 Eighth Avenue", "New York", "United States", "US", 40.7410, -74.0018, "carrier_hotel", "Google"),
    "ny_60hudson": FacilityLocation("60 Hudson Street", "New York", "United States", "US", 40.7195, -74.0089, "carrier_hotel", "Various"),
    "ny_32avenue": FacilityLocation("32 Avenue of the Americas", "New York", "United States", "US", 40.7189, -74.0049, "carrier_hotel", "Various"),
    "ny_165halsey": FacilityLocation("165 Halsey Street", "Newark", "United States", "US", 40.7380, -74.1694, "carrier_hotel", "Various"),
    
    # Los Angeles
    "la_onetimes": FacilityLocation("One Wilshire", "Los Angeles", "United States", "US", 34.0549, -118.2571, "carrier_hotel", "Various"),
    "la_coresite": FacilityLocation("CoreSite LA1", "Los Angeles", "United States", "US", 34.0549, -118.2426, "carrier_hotel", "CoreSite"),
    
    # Miami
    "mia_nap": FacilityLocation("NAP of the Americas", "Miami", "United States", "US", 25.7826, -80.1832, "carrier_hotel", "Verizon"),
    
    # Amsterdam
    "ams_sara": FacilityLocation("SARA Amsterdam", "Amsterdam", "Netherlands", "NL", 52.3563, 4.9543, "carrier_hotel", "Nikhef"),
    
    # Frankfurt  
    "fra_interxion": FacilityLocation("Interxion Frankfurt", "Frankfurt", "Germany", "DE", 50.1109, 8.6821, "carrier_hotel", "Interxion"),
}


# =============================================================================
# ASN TO DATACENTER MAPPING (Known hosting providers)
# =============================================================================

HOSTING_PROVIDER_ASNS: dict[str, dict] = {
    # Major Cloud Providers
    "15169": {"name": "Google", "type": "cloud", "color": "#4285F4", "hq_lat": 37.4220, "hq_lon": -122.0841},
    "396982": {"name": "Google Cloud", "type": "cloud", "color": "#4285F4", "hq_lat": 37.4220, "hq_lon": -122.0841},
    "16509": {"name": "Amazon AWS", "type": "cloud", "color": "#FF9900", "hq_lat": 47.6062, "hq_lon": -122.3321},
    "14618": {"name": "Amazon AWS", "type": "cloud", "color": "#FF9900", "hq_lat": 39.0438, "hq_lon": -77.4874},
    "8075": {"name": "Microsoft Azure", "type": "cloud", "color": "#00A4EF", "hq_lat": 47.6740, "hq_lon": -122.1215},
    "8068": {"name": "Microsoft", "type": "cloud", "color": "#00A4EF", "hq_lat": 47.6740, "hq_lon": -122.1215},
    "13335": {"name": "Cloudflare", "type": "cdn", "color": "#F38020", "hq_lat": 37.7749, "hq_lon": -122.4194},
    "20940": {"name": "Akamai", "type": "cdn", "color": "#0096D6", "hq_lat": 42.3601, "hq_lon": -71.0589},
    "54113": {"name": "Fastly", "type": "cdn", "color": "#FF282D", "hq_lat": 37.7749, "hq_lon": -122.4194},
    "32934": {"name": "Facebook/Meta", "type": "cloud", "color": "#1877F2", "hq_lat": 37.4845, "hq_lon": -122.1477},
    "714": {"name": "Apple", "type": "cloud", "color": "#A2AAAD", "hq_lat": 37.3349, "hq_lon": -122.0090},
    "2906": {"name": "Netflix", "type": "cdn", "color": "#E50914", "hq_lat": 37.2608, "hq_lon": -121.9849},
    "36459": {"name": "GitHub", "type": "cloud", "color": "#333333", "hq_lat": 37.7749, "hq_lon": -122.4194},
    
    # VPS/Hosting Providers
    "14061": {"name": "DigitalOcean", "type": "cloud", "color": "#0080FF", "hq_lat": 40.7128, "hq_lon": -74.0060},
    "63949": {"name": "Linode/Akamai", "type": "cloud", "color": "#00A95C", "hq_lat": 39.9526, "hq_lon": -75.1652},
    "20473": {"name": "Vultr", "type": "cloud", "color": "#007BFC", "hq_lat": 40.7128, "hq_lon": -74.0060},
    "24940": {"name": "Hetzner", "type": "cloud", "color": "#D50C2D", "hq_lat": 50.9575, "hq_lon": 11.0304},
    "51167": {"name": "Contabo", "type": "cloud", "color": "#1E3A5F", "hq_lat": 48.1351, "hq_lon": 11.5820},
    "16276": {"name": "OVH", "type": "cloud", "color": "#123456", "hq_lat": 50.6927, "hq_lon": 3.1723},
    "60781": {"name": "LeaseWeb", "type": "cloud", "color": "#E31937", "hq_lat": 52.3676, "hq_lon": 4.9041},
    "29802": {"name": "HiVelocity", "type": "cloud", "color": "#FF6600", "hq_lat": 27.9506, "hq_lon": -82.4572},
    
    # UK Specific
    "2856": {"name": "BT", "type": "isp", "color": "#5514B4", "hq_lat": 51.5074, "hq_lon": -0.1278},
    "5089": {"name": "Virgin Media", "type": "isp", "color": "#CC0000", "hq_lat": 51.3148, "hq_lon": -0.5600},
    "13285": {"name": "TalkTalk", "type": "isp", "color": "#8C1EDF", "hq_lat": 51.3891, "hq_lon": -0.0116},
    "5607": {"name": "Sky UK", "type": "isp", "color": "#0072CE", "hq_lat": 51.4872, "hq_lon": -0.3518},
    "6871": {"name": "Plusnet", "type": "isp", "color": "#FFA500", "hq_lat": 53.3811, "hq_lon": -1.4701},
    "12576": {"name": "EE", "type": "isp", "color": "#00B8F1", "hq_lat": 51.5074, "hq_lon": -0.1278},
    "31655": {"name": "Gamma Telecom", "type": "isp", "color": "#00A651", "hq_lat": 52.4774, "hq_lon": -1.8982},
    "8468": {"name": "Entanet", "type": "isp", "color": "#1E90FF", "hq_lat": 51.5074, "hq_lon": -0.1278},
    "20712": {"name": "Andrews & Arnold", "type": "isp", "color": "#006400", "hq_lat": 51.8860, "hq_lon": -0.4167},
    "61323": {"name": "Zen Internet", "type": "isp", "color": "#FF6600", "hq_lat": 53.3936, "hq_lon": -2.1450},
    
    # Major Transit/Tier 1
    "174": {"name": "Cogent", "type": "transit", "color": "#FF6600", "hq_lat": 38.9072, "hq_lon": -77.0369},
    "3356": {"name": "Lumen/Level3", "type": "transit", "color": "#00AEEF", "hq_lat": 39.7392, "hq_lon": -104.9903},
    "1299": {"name": "Telia", "type": "transit", "color": "#990AE3", "hq_lat": 59.3293, "hq_lon": 18.0686},
    "2914": {"name": "NTT", "type": "transit", "color": "#ED1C24", "hq_lat": 35.6762, "hq_lon": 139.6503},
    "6762": {"name": "Sparkle", "type": "transit", "color": "#0066B3", "hq_lat": 41.9028, "hq_lon": 12.4964},
    "3257": {"name": "GTT", "type": "transit", "color": "#00A0DF", "hq_lat": 38.9072, "hq_lon": -77.0369},
    "6461": {"name": "Zayo", "type": "transit", "color": "#003DA6", "hq_lat": 40.0150, "hq_lon": -105.2705},
    "6939": {"name": "Hurricane Electric", "type": "transit", "color": "#ED1C24", "hq_lat": 37.4923, "hq_lon": -122.2110},
    "1273": {"name": "Vodafone", "type": "transit", "color": "#E60000", "hq_lat": 51.5539, "hq_lon": -0.4847},
    "5511": {"name": "Orange", "type": "transit", "color": "#FF7900", "hq_lat": 48.8566, "hq_lon": 2.3522},
    "3320": {"name": "Deutsche Telekom", "type": "transit", "color": "#E20074", "hq_lat": 50.9375, "hq_lon": 6.9603},
}


def get_facility_by_ip_prefix(ip: str) -> FacilityLocation | None:
    """Look up facility by IP prefix match."""
    import ipaddress
    
    try:
        ip_obj = ipaddress.ip_address(ip)
        
        # Check IXP prefixes
        for prefix, facility in IXP_PREFIXES.items():
            try:
                network = ipaddress.ip_network(prefix, strict=False)
                if ip_obj in network:
                    return facility
            except ValueError:
                continue
                
    except ValueError:
        pass
    
    return None


def get_provider_info(asn: str) -> dict | None:
    """Get provider info by ASN."""
    asn_clean = str(asn).replace("AS", "")
    return HOSTING_PROVIDER_ASNS.get(asn_clean)


def get_all_facilities() -> list[FacilityLocation]:
    """Get all known facilities for map display."""
    facilities = []
    
    # Add all IXPs (deduplicated by name)
    seen_names = set()
    for facility in IXP_PREFIXES.values():
        if facility.name not in seen_names:
            facilities.append(facility)
            seen_names.add(facility.name)
    
    # Add datacenters
    facilities.extend(DATACENTER_LOCATIONS.values())
    
    # Add UK telecom exchanges
    facilities.extend(UK_TELECOM_EXCHANGES.values())
    
    # Add cable landing stations
    facilities.extend(CABLE_LANDING_STATIONS.values())
    
    # Add POPs
    facilities.extend(POPS.values())
    
    # Add carrier hotels
    facilities.extend(CARRIER_HOTELS.values())
    
    return facilities


# =============================================================================
# MOBILE NETWORK INFRASTRUCTURE
# =============================================================================
# Mobile Network Operator ASNs and their typical tower/infrastructure locations
# Used to identify when traceroute hops are passing through mobile infrastructure

MOBILE_NETWORK_ASNS: dict[str, dict] = {
    # UK Mobile Networks
    "12576": {"name": "EE (UK)", "country": "GB", "type": "mobile"},
    "6871": {"name": "EE (UK)", "country": "GB", "type": "mobile"},
    "2856": {"name": "BT Mobile", "country": "GB", "type": "mobile"},
    "12703": {"name": "Three UK", "country": "GB", "type": "mobile"},
    "60339": {"name": "Three UK", "country": "GB", "type": "mobile"},
    "34848": {"name": "Vodafone UK", "country": "GB", "type": "mobile"},
    "1273": {"name": "Vodafone UK", "country": "GB", "type": "mobile"},
    "25135": {"name": "O2 UK", "country": "GB", "type": "mobile"},
    "5378": {"name": "O2 UK", "country": "GB", "type": "mobile"},
    "15706": {"name": "Virgin Mobile UK", "country": "GB", "type": "mobile"},
    
    # US Mobile Networks
    "7018": {"name": "AT&T Mobility", "country": "US", "type": "mobile"},
    "20057": {"name": "AT&T Mobility", "country": "US", "type": "mobile"},
    "22394": {"name": "Verizon Wireless", "country": "US", "type": "mobile"},
    "6167": {"name": "Verizon Wireless", "country": "US", "type": "mobile"},
    "21928": {"name": "T-Mobile US", "country": "US", "type": "mobile"},
    "20001": {"name": "T-Mobile US", "country": "US", "type": "mobile"},
    
    # European Mobile Networks
    "3320": {"name": "Deutsche Telekom", "country": "DE", "type": "mobile"},
    "6805": {"name": "Telefonica Germany", "country": "DE", "type": "mobile"},
    "8881": {"name": "Vodafone Germany", "country": "DE", "type": "mobile"},
    "12322": {"name": "Free Mobile (FR)", "country": "FR", "type": "mobile"},
    "15557": {"name": "SFR (FR)", "country": "FR", "type": "mobile"},
    "5511": {"name": "Orange France", "country": "FR", "type": "mobile"},
    
    # Other Global Mobile Networks
    "9498": {"name": "Bharti Airtel", "country": "IN", "type": "mobile"},
    "24560": {"name": "Jio", "country": "IN", "type": "mobile"},
    "4788": {"name": "Telkomsel", "country": "ID", "type": "mobile"},
    "17974": {"name": "Telstra Mobile", "country": "AU", "type": "mobile"},
    "7545": {"name": "Optus", "country": "AU", "type": "mobile"},
}


# Known cell tower location databases - IP ranges that indicate mobile infrastructure
# These are typically CGNAT (Carrier-Grade NAT) ranges used by mobile operators
MOBILE_CGNAT_RANGES: dict[str, dict] = {
    # Common CGNAT ranges used by mobile operators
    "100.64.0.0/10": {"type": "cgnat", "note": "CGNAT - Mobile/ISP"},
    "10.0.0.0/8": {"type": "private", "note": "Private - Could be mobile backhaul"},
    
    # EE UK Mobile
    "90.192.0.0/11": {"carrier": "EE UK", "type": "mobile_pool"},
    "90.240.0.0/12": {"carrier": "EE UK", "type": "mobile_pool"},
    
    # Three UK
    "86.128.0.0/10": {"carrier": "Three UK", "type": "mobile_pool"},
    
    # Vodafone UK
    "92.232.0.0/13": {"carrier": "Vodafone UK", "type": "mobile_pool"},
    
    # O2 UK
    "82.132.0.0/14": {"carrier": "O2 UK", "type": "mobile_pool"},
}


@dataclass
class CellTowerInfo:
    """Information about a detected cell tower or mobile infrastructure point."""
    carrier: str
    tower_type: str  # "4g_lte", "5g_nr", "3g_umts", "backhaul", "core"
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    country_code: str | None = None
    mcc: str | None = None  # Mobile Country Code
    mnc: str | None = None  # Mobile Network Code
    lac: str | None = None  # Location Area Code
    cell_id: str | None = None
    
    def to_dict(self) -> dict:
        return {
            "carrier": self.carrier,
            "tower_type": self.tower_type,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "city": self.city,
            "country_code": self.country_code,
            "mcc": self.mcc,
            "mnc": self.mnc,
            "lac": self.lac,
            "cell_id": self.cell_id,
        }


def detect_mobile_infrastructure(ip: str, asn: str | None = None) -> CellTowerInfo | None:
    """
    Detect if an IP belongs to mobile network infrastructure.
    
    Returns cell tower/mobile info if detected, None otherwise.
    """
    import ipaddress
    
    try:
        ip_obj = ipaddress.ip_address(ip)
        
        # Check CGNAT ranges
        for prefix, info in MOBILE_CGNAT_RANGES.items():
            try:
                network = ipaddress.ip_network(prefix, strict=False)
                if ip_obj in network:
                    return CellTowerInfo(
                        carrier=info.get("carrier", "Unknown Mobile"),
                        tower_type="cgnat",
                    )
            except ValueError:
                continue
    except ValueError:
        pass
    
    # Check ASN
    if asn:
        asn_clean = str(asn).replace("AS", "")
        if asn_clean in MOBILE_NETWORK_ASNS:
            info = MOBILE_NETWORK_ASNS[asn_clean]
            return CellTowerInfo(
                carrier=info["name"],
                tower_type="mobile_core",
                country_code=info.get("country"),
            )
    
    return None


def is_mobile_network(asn: str | None) -> bool:
    """Check if ASN belongs to a mobile network operator."""
    if not asn:
        return False
    asn_clean = str(asn).replace("AS", "")
    return asn_clean in MOBILE_NETWORK_ASNS


def get_mobile_carrier_info(asn: str) -> dict | None:
    """Get mobile carrier info by ASN."""
    asn_clean = str(asn).replace("AS", "")
    return MOBILE_NETWORK_ASNS.get(asn_clean)


# =============================================================================
# CELL TOWER GEOLOCATION API INTEGRATION
# =============================================================================
# These functions help obtain cell tower locations from various sources

async def lookup_cell_tower_location(
    mcc: str,
    mnc: str, 
    lac: str,
    cell_id: str,
    session=None,
) -> tuple[float, float] | None:
    """
    Look up cell tower location using OpenCellID or similar API.
    
    Note: Requires API key for production use. This is a placeholder
    that can be connected to:
    - OpenCellID (https://opencellid.org/)
    - Google Geolocation API
    - Mozilla Location Service
    - UnwiredLabs
    
    Returns (latitude, longitude) if found.
    """
    # Placeholder - in production, call actual API
    # Example with OpenCellID:
    # url = f"https://opencellid.org/cell/get?key={API_KEY}&mcc={mcc}&mnc={mnc}&lac={lac}&cellid={cell_id}&format=json"
    
    return None


def estimate_cell_tower_location_from_ip_geo(
    ip_lat: float,
    ip_lon: float,
    carrier: str,
) -> tuple[float, float]:
    """
    Estimate cell tower location based on IP geolocation.
    
    Cell towers are typically within a few km of the IP geolocation result.
    This provides a rough estimate when exact tower location is unknown.
    
    Returns slightly adjusted coordinates to indicate uncertainty.
    """
    # Add small random offset to indicate this is estimated
    import random
    offset_lat = random.uniform(-0.01, 0.01)  # ~1km
    offset_lon = random.uniform(-0.01, 0.01)
    
    return (ip_lat + offset_lat, ip_lon + offset_lon)


# =============================================================================
# INFRASTRUCTURE CLASSIFICATION
# =============================================================================

def classify_infrastructure(
    ip: str,
    asn: str | None = None,
    hostname: str | None = None,
) -> dict[str, Any]:
    """
    Classify an IP address into infrastructure type.
    
    Returns dict with:
    - is_permanent: True if should stay on map forever
    - facility_type: Type of infrastructure
    - facility_info: Detailed info if available
    """
    result = {
        "is_permanent": False,
        "facility_type": "unknown",
        "facility_info": None,
    }
    
    # Check if it's a known facility
    facility = get_facility_by_ip_prefix(ip)
    if facility:
        result["is_permanent"] = True
        result["facility_type"] = facility.facility_type
        result["facility_info"] = facility.to_dict()
        return result
    
    # Check if it's mobile infrastructure
    mobile_info = detect_mobile_infrastructure(ip, asn)
    if mobile_info:
        result["is_permanent"] = True  # Cell infrastructure is permanent
        result["facility_type"] = "cell_tower"
        result["facility_info"] = mobile_info.to_dict()
        return result
    
    # Check hosting providers (datacenters are permanent)
    if asn:
        provider = get_provider_info(asn)
        if provider:
            if provider.get("type") in ("cloud", "hosting"):
                result["is_permanent"] = True
                result["facility_type"] = "datacenter"
            elif provider.get("type") == "cdn":
                result["is_permanent"] = True
                result["facility_type"] = "cdn_pop"
            result["facility_info"] = provider
            return result
    
    # Check hostname patterns for infrastructure
    if hostname:
        hostname_lower = hostname.lower()
        
        # Cell tower / mobile patterns
        if any(p in hostname_lower for p in ["cell", "tower", "lte", "5g", "enodeb", "gnodeb"]):
            result["is_permanent"] = True
            result["facility_type"] = "cell_tower"
            return result
        
        # Datacenter patterns
        if any(p in hostname_lower for p in ["dc", "datacenter", "colo", "equinix", "interxion"]):
            result["is_permanent"] = True
            result["facility_type"] = "datacenter"
            return result
        
        # IXP patterns
        if any(p in hostname_lower for p in ["ix", "exchange", "peering", "linx", "amsix", "decix"]):
            result["is_permanent"] = True
            result["facility_type"] = "ixp"
            return result
    
    return result

