"""API client for HAM Network peer discovery and communication."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import aiohttp

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class Peer:
    """Represents a peer Home Assistant instance."""
    
    peer_id: str
    display_name: str
    latitude: float
    longitude: float
    public_ip: str | None = None
    public_url: str | None = None
    last_seen: datetime | None = None
    online: bool = False
    version: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "peer_id": self.peer_id,
            "display_name": self.display_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "public_ip": self.public_ip,
            "public_url": self.public_url,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "online": self.online,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Peer:
        """Create from dictionary."""
        last_seen = None
        if data.get("last_seen"):
            try:
                last_seen = datetime.fromisoformat(data["last_seen"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            peer_id=data["peer_id"],
            display_name=data["display_name"],
            latitude=data["latitude"],
            longitude=data["longitude"],
            public_ip=data.get("public_ip"),
            public_url=data.get("public_url"),
            last_seen=last_seen,
            online=data.get("online", False),
            version=data.get("version"),
        )


@dataclass
class NetworkTopologyLink:
    """Represents a link between two peers in the network topology."""
    
    source_peer_id: str
    target_peer_id: str
    latency_ms: float | None = None
    hop_count: int | None = None
    last_measured: datetime | None = None
    hops: list[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source_peer_id,
            "target": self.target_peer_id,
            "latency_ms": self.latency_ms,
            "hop_count": self.hop_count,
            "last_measured": self.last_measured.isoformat() if self.last_measured else None,
            "hops": self.hops,
        }


class HAMNetworkAPI:
    """API client for HAM Network discovery server."""
    
    def __init__(
        self,
        discovery_server: str,
        peer_id: str,
        display_name: str,
        latitude: float,
        longitude: float,
        public_url: str | None = None,
    ) -> None:
        """Initialize the API client."""
        self._discovery_server = discovery_server.rstrip("/")
        self._peer_id = peer_id
        self._display_name = display_name
        self._latitude = latitude
        self._longitude = longitude
        self._public_url = public_url
        self._session: aiohttp.ClientSession | None = None
        self._public_ip: str | None = None
    
    async def async_init(self) -> None:
        """Initialize async components."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        
        # Get our public IP
        from .network import get_public_ip
        self._public_ip = await get_public_ip()
    
    async def async_close(self) -> None:
        """Close the API client."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def async_register(self) -> bool:
        """Register this instance with the discovery server."""
        if not self._session:
            await self.async_init()
        
        data = {
            "peer_id": self._peer_id,
            "display_name": self._display_name,
            "latitude": self._latitude,
            "longitude": self._longitude,
            "public_ip": self._public_ip,
            "public_url": self._public_url,
        }
        
        try:
            url = f"{self._discovery_server}/api/peers/register"
            async with self._session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    _LOGGER.info("Successfully registered with discovery server")
                    return True
                else:
                    _LOGGER.warning("Failed to register: %s", await response.text())
                    return False
        except aiohttp.ClientError as e:
            _LOGGER.error("Error registering with discovery server: %s", e)
            return False
    
    async def async_heartbeat(self) -> bool:
        """Send heartbeat to discovery server."""
        if not self._session:
            await self.async_init()
        
        try:
            url = f"{self._discovery_server}/api/peers/{self._peer_id}/heartbeat"
            async with self._session.post(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200
        except aiohttp.ClientError as e:
            _LOGGER.debug("Heartbeat failed: %s", e)
            return False
    
    async def async_get_peers(self) -> list[Peer]:
        """Get list of all registered peers."""
        if not self._session:
            await self.async_init()
        
        peers: list[Peer] = []
        
        try:
            url = f"{self._discovery_server}/api/peers"
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    for peer_data in data.get("peers", []):
                        # Don't include ourselves
                        if peer_data.get("peer_id") != self._peer_id:
                            peers.append(Peer.from_dict(peer_data))
        except aiohttp.ClientError as e:
            _LOGGER.error("Error fetching peers: %s", e)
        
        return peers
    
    async def async_submit_traceroute(
        self,
        target_peer_id: str,
        traceroute_result: dict,
    ) -> bool:
        """Submit traceroute results to the discovery server."""
        if not self._session:
            await self.async_init()
        
        data = {
            "source_peer_id": self._peer_id,
            "target_peer_id": target_peer_id,
            "traceroute": traceroute_result,
        }
        
        try:
            url = f"{self._discovery_server}/api/topology/traceroute"
            async with self._session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                return response.status == 200
        except aiohttp.ClientError as e:
            _LOGGER.error("Error submitting traceroute: %s", e)
            return False
    
    async def async_get_topology(self) -> dict[str, Any]:
        """Get the full network topology from the discovery server."""
        if not self._session:
            await self.async_init()
        
        try:
            url = f"{self._discovery_server}/api/topology"
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    return await response.json()
        except aiohttp.ClientError as e:
            _LOGGER.error("Error fetching topology: %s", e)
        
        return {"peers": [], "links": []}
    
    @property
    def peer_id(self) -> str:
        """Return the peer ID."""
        return self._peer_id
    
    @property
    def public_ip(self) -> str | None:
        """Return the public IP."""
        return self._public_ip


class MockDiscoveryServer:
    """
    Mock discovery server for local development and testing.
    
    In production, this would be replaced by a real server.
    This allows the integration to work standalone for demo purposes.
    """
    
    _peers: dict[str, Peer] = {}
    _topology_links: list[NetworkTopologyLink] = []
    
    @classmethod
    def register_peer(cls, peer: Peer) -> None:
        """Register a peer."""
        peer.last_seen = datetime.now()
        peer.online = True
        cls._peers[peer.peer_id] = peer
    
    @classmethod
    def get_peers(cls) -> list[Peer]:
        """Get all peers."""
        return list(cls._peers.values())
    
    @classmethod
    def add_topology_link(cls, link: NetworkTopologyLink) -> None:
        """Add or update a topology link."""
        # Remove existing link if present
        cls._topology_links = [
            l for l in cls._topology_links 
            if not (l.source_peer_id == link.source_peer_id and l.target_peer_id == link.target_peer_id)
        ]
        link.last_measured = datetime.now()
        cls._topology_links.append(link)
    
    @classmethod
    def get_topology(cls) -> dict[str, Any]:
        """Get full topology."""
        return {
            "peers": [p.to_dict() for p in cls._peers.values()],
            "links": [l.to_dict() for l in cls._topology_links],
        }
