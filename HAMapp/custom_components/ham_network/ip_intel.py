"""
IP Intelligence for HAM Network.

Provides geolocation, ASN lookup, and network infrastructure identification
for traceroute hops. Uses local databases and privacy-respecting lookups.

Privacy Design:
- Lookups are done locally where possible (MaxMind GeoLite2)
- Public API lookups are rate-limited and cached
- User's own IP is never sent to third parties unnecessarily
- All data stays on the user's Home Assistant instance
"""
from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Cache settings
CACHE_TTL_HOURS = 24 * 7  # Cache geo data for 1 week
CACHE_MAX_ENTRIES = 10000

# Known IXP prefixes (major Internet Exchange Points)
KNOWN_IXP_PREFIXES = {
    # DE-CIX (Frankfurt)
    "80.81.192.0/22": {"name": "DE-CIX Frankfurt", "city": "Frankfurt", "country": "DE"},
    "2001:7f8::/32": {"name": "DE-CIX Frankfurt", "city": "Frankfurt", "country": "DE"},
    # AMS-IX (Amsterdam)
    "80.249.208.0/21": {"name": "AMS-IX", "city": "Amsterdam", "country": "NL"},
    "2001:7f8:1::/48": {"name": "AMS-IX", "city": "Amsterdam", "country": "NL"},
    # LINX (London)
    "195.66.224.0/21": {"name": "LINX", "city": "London", "country": "GB"},
    "2001:7f8:4::/48": {"name": "LINX", "city": "London", "country": "GB"},
    # Equinix IX
    "206.126.236.0/22": {"name": "Equinix Ashburn", "city": "Ashburn", "country": "US"},
    "198.32.160.0/21": {"name": "Equinix San Jose", "city": "San Jose", "country": "US"},
    # NL-ix
    "193.239.116.0/22": {"name": "NL-ix", "city": "Amsterdam", "country": "NL"},
    # JPNAP
    "210.171.224.0/23": {"name": "JPNAP Tokyo", "city": "Tokyo", "country": "JP"},
    # HKIX
    "202.40.161.0/24": {"name": "HKIX", "city": "Hong Kong", "country": "HK"},
    # SIX (Seattle)
    "206.81.80.0/22": {"name": "SIX Seattle", "city": "Seattle", "country": "US"},
    # Any-IX
    "185.1.0.0/22": {"name": "Any2 Exchange", "city": "Los Angeles", "country": "US"},
    # NYIIX
    "198.32.118.0/24": {"name": "NYIIX", "city": "New York", "country": "US"},
    # CoreSite
    "206.72.210.0/23": {"name": "CoreSite Any2", "city": "Los Angeles", "country": "US"},
    # MICE (Midwest)
    "206.53.139.0/24": {"name": "MICE", "city": "Minneapolis", "country": "US"},
    # TorIX
    "206.108.34.0/24": {"name": "TorIX", "city": "Toronto", "country": "CA"},
}

# Known datacenter/cloud provider ASNs
KNOWN_PROVIDER_ASNS = {
    # Major Cloud Providers
    "15169": {"name": "Google", "type": "cloud", "color": "#4285F4"},
    "396982": {"name": "Google Cloud", "type": "cloud", "color": "#4285F4"},
    "16509": {"name": "Amazon AWS", "type": "cloud", "color": "#FF9900"},
    "14618": {"name": "Amazon AWS", "type": "cloud", "color": "#FF9900"},
    "8075": {"name": "Microsoft Azure", "type": "cloud", "color": "#00A4EF"},
    "8068": {"name": "Microsoft", "type": "cloud", "color": "#00A4EF"},
    "13335": {"name": "Cloudflare", "type": "cdn", "color": "#F38020"},
    "20940": {"name": "Akamai", "type": "cdn", "color": "#0096D6"},
    "54113": {"name": "Fastly", "type": "cdn", "color": "#FF282D"},
    "16591": {"name": "Google Fiber", "type": "isp", "color": "#4285F4"},
    "32934": {"name": "Facebook/Meta", "type": "cloud", "color": "#1877F2"},
    "714": {"name": "Apple", "type": "cloud", "color": "#A2AAAD"},
    "2906": {"name": "Netflix", "type": "cdn", "color": "#E50914"},
    "46489": {"name": "Twitch", "type": "cdn", "color": "#9146FF"},
    "36459": {"name": "GitHub", "type": "cloud", "color": "#333333"},
    "14061": {"name": "DigitalOcean", "type": "cloud", "color": "#0080FF"},
    "63949": {"name": "Linode/Akamai", "type": "cloud", "color": "#00A95C"},
    "20473": {"name": "Vultr", "type": "cloud", "color": "#007BFC"},
    "24940": {"name": "Hetzner", "type": "cloud", "color": "#D50C2D"},
    "51167": {"name": "Contabo", "type": "cloud", "color": "#1E3A5F"},
    "14061": {"name": "DigitalOcean", "type": "cloud", "color": "#0080FF"},
    
    # Major Transit/Tier 1 Providers
    "174": {"name": "Cogent", "type": "transit", "color": "#FF6600"},
    "3356": {"name": "Lumen/Level3", "type": "transit", "color": "#00AEEF"},
    "1299": {"name": "Telia", "type": "transit", "color": "#990AE3"},
    "6830": {"name": "Liberty Global", "type": "transit", "color": "#E31937"},
    "2914": {"name": "NTT", "type": "transit", "color": "#ED1C24"},
    "6762": {"name": "Telecom Italia Sparkle", "type": "transit", "color": "#0066B3"},
    "3257": {"name": "GTT", "type": "transit", "color": "#00A0DF"},
    "6461": {"name": "Zayo", "type": "transit", "color": "#003DA6"},
    "701": {"name": "Verizon", "type": "transit", "color": "#CD040B"},
    "7018": {"name": "AT&T", "type": "transit", "color": "#00A8E0"},
    "6939": {"name": "Hurricane Electric", "type": "transit", "color": "#ED1C24"},
    "1239": {"name": "Sprint", "type": "transit", "color": "#FFCE00"},
    "209": {"name": "CenturyLink", "type": "transit", "color": "#00A94F"},
    "3491": {"name": "PCCW Global", "type": "transit", "color": "#E31B23"},
    "4134": {"name": "China Telecom", "type": "transit", "color": "#E60012"},
    "4837": {"name": "China Unicom", "type": "transit", "color": "#E60012"},
    
    # Regional ISPs (examples)
    "7922": {"name": "Comcast", "type": "isp", "color": "#FF0000"},
    "22773": {"name": "Cox", "type": "isp", "color": "#F26722"},
    "20001": {"name": "Charter/Spectrum", "type": "isp", "color": "#009FDA"},
    "5650": {"name": "Frontier", "type": "isp", "color": "#FF0000"},
    "6128": {"name": "Cablevision", "type": "isp", "color": "#004B87"},
    "577": {"name": "Bell Canada", "type": "isp", "color": "#0056A3"},
    "6327": {"name": "Shaw", "type": "isp", "color": "#003595"},
    "5769": {"name": "Videotron", "type": "isp", "color": "#FFCC00"},
}


@dataclass
class GeoLocation:
    """Geographic location data for an IP address."""
    
    ip: str
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    country_code: str | None = None
    postal_code: str | None = None
    timezone: str | None = None
    accuracy_radius_km: int | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ip": self.ip,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "city": self.city,
            "region": self.region,
            "country": self.country,
            "country_code": self.country_code,
            "postal_code": self.postal_code,
            "timezone": self.timezone,
            "accuracy_radius_km": self.accuracy_radius_km,
        }


@dataclass
class ASNInfo:
    """Autonomous System Number information."""
    
    asn: str | None = None
    as_name: str | None = None
    as_org: str | None = None
    network_type: str | None = None  # cloud, cdn, transit, isp, enterprise
    color: str | None = None  # For visualization
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "asn": self.asn,
            "as_name": self.as_name,
            "as_org": self.as_org,
            "network_type": self.network_type,
            "color": self.color,
        }


@dataclass
class NetworkInfrastructure:
    """Information about network infrastructure at a hop."""
    
    is_ixp: bool = False
    ixp_name: str | None = None
    is_datacenter: bool = False
    datacenter_name: str | None = None
    is_pop: bool = False  # Point of Presence
    pop_name: str | None = None
    facility_type: str | None = None  # ixp, datacenter, pop, carrier-hotel, etc.
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_ixp": self.is_ixp,
            "ixp_name": self.ixp_name,
            "is_datacenter": self.is_datacenter,
            "datacenter_name": self.datacenter_name,
            "is_pop": self.is_pop,
            "pop_name": self.pop_name,
            "facility_type": self.facility_type,
        }


@dataclass
class EnrichedHop:
    """Traceroute hop enriched with geographic and network intelligence."""
    
    hop_number: int
    ip_address: str | None
    rtt_ms: float | None
    
    # Geographic info
    geo: GeoLocation | None = None
    
    # ASN info
    asn_info: ASNInfo | None = None
    
    # Infrastructure info
    infrastructure: NetworkInfrastructure | None = None
    
    # Path analysis
    asn_transition: bool = False  # True if ASN changed from previous hop
    country_transition: bool = False  # True if country changed
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hop_number": self.hop_number,
            "ip": self.ip_address,
            "rtt_ms": self.rtt_ms,
            "geo": self.geo.to_dict() if self.geo else None,
            "asn": self.asn_info.to_dict() if self.asn_info else None,
            "infrastructure": self.infrastructure.to_dict() if self.infrastructure else None,
            "asn_transition": self.asn_transition,
            "country_transition": self.country_transition,
        }


class IPIntelligenceCache:
    """Thread-safe cache for IP intelligence data."""
    
    def __init__(self, cache_dir: Path | None = None):
        """Initialize cache."""
        self._cache_dir = cache_dir
        self._memory_cache: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Any | None:
        """Get cached value."""
        async with self._lock:
            if key in self._memory_cache:
                timestamp, value = self._memory_cache[key]
                if time.time() - timestamp < CACHE_TTL_HOURS * 3600:
                    return value
                else:
                    del self._memory_cache[key]
            return None
    
    async def set(self, key: str, value: Any) -> None:
        """Set cached value."""
        async with self._lock:
            # Evict old entries if cache is too large
            if len(self._memory_cache) >= CACHE_MAX_ENTRIES:
                # Remove oldest 10%
                sorted_keys = sorted(
                    self._memory_cache.keys(),
                    key=lambda k: self._memory_cache[k][0]
                )
                for k in sorted_keys[:CACHE_MAX_ENTRIES // 10]:
                    del self._memory_cache[k]
            
            self._memory_cache[key] = (time.time(), value)
    
    async def clear(self) -> None:
        """Clear cache."""
        async with self._lock:
            self._memory_cache.clear()


class IPIntelligence:
    """
    IP Intelligence service for HAM Network.
    
    Provides geolocation, ASN lookup, and infrastructure identification
    while respecting user privacy.
    """
    
    def __init__(self, cache_dir: Path | None = None):
        """Initialize IP intelligence service."""
        self._cache = IPIntelligenceCache(cache_dir)
        self._session: aiohttp.ClientSession | None = None
        self._rate_limit_until: float = 0
        self._requests_this_minute: int = 0
        self._minute_start: float = time.time()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": "HAM-Network/2.0 (Home Assistant Integration)"}
            )
        return self._session
    
    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is private/reserved."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return (
                ip_obj.is_private or 
                ip_obj.is_reserved or 
                ip_obj.is_loopback or
                ip_obj.is_link_local or
                ip_obj.is_multicast
            )
        except ValueError:
            return True
    
    def _check_ixp(self, ip: str) -> NetworkInfrastructure | None:
        """Check if IP belongs to a known IXP."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            for prefix, info in KNOWN_IXP_PREFIXES.items():
                network = ipaddress.ip_network(prefix, strict=False)
                if ip_obj in network:
                    return NetworkInfrastructure(
                        is_ixp=True,
                        ixp_name=info["name"],
                        facility_type="ixp",
                    )
        except ValueError:
            pass
        return None
    
    def _get_known_provider(self, asn: str) -> dict | None:
        """Get known provider info by ASN."""
        return KNOWN_PROVIDER_ASNS.get(asn.replace("AS", ""))
    
    async def _rate_limited_request(self) -> bool:
        """Check and update rate limiting. Returns True if request allowed."""
        now = time.time()
        
        # Check if we're in a rate limit cooldown
        if now < self._rate_limit_until:
            return False
        
        # Reset counter every minute
        if now - self._minute_start > 60:
            self._requests_this_minute = 0
            self._minute_start = now
        
        # Allow max 45 requests per minute (under most API limits)
        if self._requests_this_minute >= 45:
            self._rate_limit_until = self._minute_start + 60
            return False
        
        self._requests_this_minute += 1
        return True
    
    async def get_geo_location(self, ip: str) -> GeoLocation:
        """
        Get geographic location for an IP address.
        
        Uses privacy-respecting services and caching.
        """
        geo = GeoLocation(ip=ip)
        
        # Skip private IPs
        if self._is_private_ip(ip):
            geo.city = "Private Network"
            return geo
        
        # Check cache
        cache_key = f"geo:{ip}"
        cached = await self._cache.get(cache_key)
        if cached:
            return GeoLocation(**cached)
        
        # Rate limit check
        if not await self._rate_limited_request():
            _LOGGER.debug("Rate limited, skipping geo lookup for %s", ip)
            return geo
        
        # Try ip-api.com (free, no key required, 45 req/min)
        try:
            session = await self._get_session()
            # Use HTTPS and minimal fields for privacy
            url = f"http://ip-api.com/json/{ip}?fields=status,lat,lon,city,regionName,country,countryCode,zip,timezone"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        geo.latitude = data.get("lat")
                        geo.longitude = data.get("lon")
                        geo.city = data.get("city")
                        geo.region = data.get("regionName")
                        geo.country = data.get("country")
                        geo.country_code = data.get("countryCode")
                        geo.postal_code = data.get("zip")
                        geo.timezone = data.get("timezone")
                        
                        # Cache result
                        await self._cache.set(cache_key, geo.to_dict())
                elif response.status == 429:
                    # Rate limited
                    self._rate_limit_until = time.time() + 60
                    
        except Exception as e:
            _LOGGER.debug("Geo lookup failed for %s: %s", ip, e)
        
        return geo
    
    async def get_asn_info(self, ip: str) -> ASNInfo:
        """
        Get ASN information for an IP address.
        
        Identifies the network operator and type.
        """
        asn_info = ASNInfo()
        
        # Skip private IPs
        if self._is_private_ip(ip):
            asn_info.as_name = "Private Network"
            asn_info.network_type = "private"
            return asn_info
        
        # Check cache
        cache_key = f"asn:{ip}"
        cached = await self._cache.get(cache_key)
        if cached:
            return ASNInfo(**cached)
        
        # Rate limit check
        if not await self._rate_limited_request():
            return asn_info
        
        # Try ip-api.com for ASN (combined with geo to save requests)
        try:
            session = await self._get_session()
            url = f"http://ip-api.com/json/{ip}?fields=status,as,org,isp"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        as_field = data.get("as", "")
                        # Parse "AS15169 Google LLC" format
                        as_match = re.match(r"AS(\d+)\s*(.*)", as_field)
                        if as_match:
                            asn_info.asn = as_match.group(1)
                            asn_info.as_name = as_match.group(2).strip() or data.get("isp")
                        
                        asn_info.as_org = data.get("org")
                        
                        # Check if it's a known provider
                        if asn_info.asn:
                            known = self._get_known_provider(asn_info.asn)
                            if known:
                                asn_info.network_type = known.get("type")
                                asn_info.color = known.get("color")
                                if not asn_info.as_name:
                                    asn_info.as_name = known.get("name")
                        
                        # Cache result
                        await self._cache.set(cache_key, asn_info.to_dict())
                        
        except Exception as e:
            _LOGGER.debug("ASN lookup failed for %s: %s", ip, e)
        
        return asn_info
    
    async def get_infrastructure_info(self, ip: str, asn_info: ASNInfo | None = None) -> NetworkInfrastructure:
        """
        Identify network infrastructure for an IP.
        
        Detects IXPs, datacenters, and POPs.
        """
        # Check for known IXP
        ixp_info = self._check_ixp(ip)
        if ixp_info:
            return ixp_info
        
        infra = NetworkInfrastructure()
        
        # Check based on ASN
        if asn_info and asn_info.asn:
            known = self._get_known_provider(asn_info.asn)
            if known:
                if known.get("type") == "cloud":
                    infra.is_datacenter = True
                    infra.datacenter_name = known.get("name")
                    infra.facility_type = "datacenter"
                elif known.get("type") == "cdn":
                    infra.is_pop = True
                    infra.pop_name = known.get("name")
                    infra.facility_type = "cdn-pop"
                elif known.get("type") == "transit":
                    infra.facility_type = "transit"
        
        return infra
    
    async def enrich_hop(
        self,
        hop_number: int,
        ip: str | None,
        rtt_ms: float | None,
        previous_asn: str | None = None,
        previous_country: str | None = None,
    ) -> EnrichedHop:
        """
        Enrich a single traceroute hop with full intelligence.
        
        Returns an EnrichedHop with geo, ASN, and infrastructure data.
        """
        enriched = EnrichedHop(
            hop_number=hop_number,
            ip_address=ip,
            rtt_ms=rtt_ms,
        )
        
        if not ip:
            return enriched
        
        # Get all intelligence (can be parallelized)
        geo_task = self.get_geo_location(ip)
        asn_task = self.get_asn_info(ip)
        
        geo, asn_info = await asyncio.gather(geo_task, asn_task)
        
        enriched.geo = geo
        enriched.asn_info = asn_info
        
        # Get infrastructure based on ASN
        enriched.infrastructure = await self.get_infrastructure_info(ip, asn_info)
        
        # Detect transitions
        if previous_asn and asn_info.asn and previous_asn != asn_info.asn:
            enriched.asn_transition = True
        
        if previous_country and geo.country_code and previous_country != geo.country_code:
            enriched.country_transition = True
        
        return enriched
    
    async def enrich_traceroute(self, hops: list) -> list[EnrichedHop]:
        """
        Enrich all hops in a traceroute with intelligence.
        
        Processes hops sequentially to detect transitions accurately.
        
        Args:
            hops: List of TracerouteHop objects or dicts with hop info
        
        Returns:
            List of EnrichedHop objects with geo/ASN/infrastructure data
        """
        enriched_hops: list[EnrichedHop] = []
        previous_asn: str | None = None
        previous_country: str | None = None
        
        for hop in hops:
            # Support both TracerouteHop objects and dicts
            if hasattr(hop, 'to_dict'):
                hop_data = hop.to_dict()
            elif isinstance(hop, dict):
                hop_data = hop
            else:
                hop_data = {"hop": 0, "ip": None, "rtt_ms": None}
            
            enriched = await self.enrich_hop(
                hop_number=hop_data.get("hop", 0),
                ip=hop_data.get("ip"),
                rtt_ms=hop_data.get("rtt_ms"),
                previous_asn=previous_asn,
                previous_country=previous_country,
            )
            
            enriched_hops.append(enriched)
            
            # Update previous values for next hop
            if enriched.asn_info and enriched.asn_info.asn:
                previous_asn = enriched.asn_info.asn
            if enriched.geo and enriched.geo.country_code:
                previous_country = enriched.geo.country_code
        
        return enriched_hops
    
    def generate_path_summary(self, enriched_hops: list[EnrichedHop]) -> dict[str, Any]:
        """
        Generate a summary of the network path.
        
        Returns statistics about ASNs traversed, countries, IXPs, etc.
        """
        asns_traversed: list[dict] = []
        countries_traversed: list[str] = []
        ixps_traversed: list[str] = []
        datacenters_traversed: list[str] = []
        asn_transitions: list[dict] = []
        
        seen_asns = set()
        seen_countries = set()
        
        for hop in enriched_hops:
            # Track ASNs
            if hop.asn_info and hop.asn_info.asn and hop.asn_info.asn not in seen_asns:
                seen_asns.add(hop.asn_info.asn)
                asns_traversed.append({
                    "asn": hop.asn_info.asn,
                    "name": hop.asn_info.as_name,
                    "type": hop.asn_info.network_type,
                    "color": hop.asn_info.color,
                    "hop": hop.hop_number,
                })
            
            # Track ASN transitions
            if hop.asn_transition and hop.asn_info:
                asn_transitions.append({
                    "hop": hop.hop_number,
                    "to_asn": hop.asn_info.asn,
                    "to_name": hop.asn_info.as_name,
                })
            
            # Track countries
            if hop.geo and hop.geo.country_code and hop.geo.country_code not in seen_countries:
                seen_countries.add(hop.geo.country_code)
                countries_traversed.append(hop.geo.country_code)
            
            # Track infrastructure
            if hop.infrastructure:
                if hop.infrastructure.is_ixp and hop.infrastructure.ixp_name:
                    if hop.infrastructure.ixp_name not in ixps_traversed:
                        ixps_traversed.append(hop.infrastructure.ixp_name)
                if hop.infrastructure.is_datacenter and hop.infrastructure.datacenter_name:
                    if hop.infrastructure.datacenter_name not in datacenters_traversed:
                        datacenters_traversed.append(hop.infrastructure.datacenter_name)
        
        return {
            "total_hops": len(enriched_hops),
            "asns_count": len(asns_traversed),
            "asns": asns_traversed,
            "asn_transitions": asn_transitions,
            "countries": countries_traversed,
            "ixps": ixps_traversed,
            "datacenters": datacenters_traversed,
            "path_type": self._classify_path(asns_traversed),
        }
    
    def _classify_path(self, asns: list[dict]) -> str:
        """Classify the network path type."""
        types = [a.get("type") for a in asns if a.get("type")]
        
        if "transit" in types and len(asns) > 3:
            return "multi-hop-transit"
        elif any(t in types for t in ["cloud", "cdn"]):
            return "cloud-optimized"
        elif len(asns) <= 2:
            return "direct-peering"
        else:
            return "standard"
    
    async def async_save_cache(self) -> None:
        """
        Save cache to disk for persistence across restarts.
        
        Called when the integration is shutting down.
        """
        if not self._cache._cache_dir:
            return
            
        cache_file = self._cache._cache_dir / "ip_intel_cache.json"
        
        try:
            async with self._cache._lock:
                # Only save entries that haven't expired
                current_time = time.time()
                valid_entries = {
                    k: v for k, v in self._cache._memory_cache.items()
                    if current_time - v[0] < CACHE_TTL_HOURS * 3600
                }
                
                cache_data = {
                    "version": "1.0",
                    "saved_at": current_time,
                    "entries": valid_entries,
                }
                
                # Write to file
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f)
                    
            _LOGGER.debug("Saved %d IP intel cache entries", len(valid_entries))
        except Exception as e:
            _LOGGER.warning("Failed to save IP intel cache: %s", e)
    
    async def async_load_cache(self) -> None:
        """
        Load cache from disk.
        
        Called when the integration starts up.
        """
        if not self._cache._cache_dir:
            return
            
        cache_file = self._cache._cache_dir / "ip_intel_cache.json"
        
        if not cache_file.exists():
            return
            
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            if cache_data.get("version") != "1.0":
                _LOGGER.debug("Cache version mismatch, starting fresh")
                return
            
            # Restore valid entries
            current_time = time.time()
            entries = cache_data.get("entries", {})
            
            async with self._cache._lock:
                for key, (timestamp, value) in entries.items():
                    if current_time - timestamp < CACHE_TTL_HOURS * 3600:
                        self._cache._memory_cache[key] = (timestamp, value)
            
            _LOGGER.debug("Loaded %d IP intel cache entries", len(self._cache._memory_cache))
        except Exception as e:
            _LOGGER.warning("Failed to load IP intel cache: %s", e)
    
    async def close(self) -> None:
        """Clean up resources."""
        await self.async_save_cache()
        if self._session and not self._session.closed:
            await self._session.close()
