"""
DHT-Based Sharding for HAM Network.

Implements distributed hash table (DHT) storage so the network can scale
to millions of nodes without each instance storing everything.

Key Concepts:
- Data is sharded by geographic region (geohash)
- Each node is responsible for data in nearby regions
- Permanent infrastructure (datacenters, IXPs, cell towers) is replicated more widely
- Transient data (traceroutes, peer locations) expires and is loaded on-demand
- Node responsibility is determined by XOR distance in the DHT keyspace

Sharding Strategy:
1. Geographic Sharding: Data partitioned by geohash prefix (e.g., "gcpv" for London area)
2. Infrastructure Always Available: High-value permanent data replicated to more nodes
3. On-Demand Loading: Nodes fetch data for regions they're viewing on the map
4. Graceful Decay: Stale data expires, disconnected nodes decay from view
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Geohash precision levels
GEOHASH_PRECISION_REGION = 3   # ~156km x 156km - for regional sharding
GEOHASH_PRECISION_CITY = 4     # ~39km x 19km - for city-level data
GEOHASH_PRECISION_LOCAL = 5    # ~5km x 5km - for local infrastructure


class DataType(Enum):
    """Types of data stored in the DHT."""
    TRACEROUTE = "traceroute"           # Transient - expires after 24h
    PEER_LOCATION = "peer"              # Transient - expires after 1h if no heartbeat
    INFRASTRUCTURE = "infrastructure"   # Permanent - replicated widely
    CELL_TOWER = "cell_tower"           # Permanent - replicated widely
    MOBILE_TRACE = "mobile_trace"       # Transient - expires after 24h


@dataclass
class ShardedData:
    """Data item stored in the DHT."""
    data_id: str
    data_type: DataType
    geohash: str  # Geographic location for sharding
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    ttl: int = 86400  # Time to live in seconds (default 24h)
    replication_factor: int = 3  # How many nodes should store this
    is_permanent: bool = False  # If true, never expires
    source_peer_id: str = ""
    
    @property
    def is_expired(self) -> bool:
        """Check if data has expired."""
        if self.is_permanent:
            return False
        return time.time() > self.timestamp + self.ttl
    
    @property
    def shard_key(self) -> str:
        """Get the shard key for DHT routing."""
        # Combine geohash prefix with data type for sharding
        prefix = self.geohash[:GEOHASH_PRECISION_REGION] if self.geohash else "global"
        return f"{prefix}:{self.data_type.value}"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "data_id": self.data_id,
            "data_type": self.data_type.value,
            "geohash": self.geohash,
            "data": self.data,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "replication_factor": self.replication_factor,
            "is_permanent": self.is_permanent,
            "source_peer_id": self.source_peer_id,
        }
    
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ShardedData:
        return cls(
            data_id=d["data_id"],
            data_type=DataType(d["data_type"]),
            geohash=d.get("geohash", ""),
            data=d.get("data", {}),
            timestamp=d.get("timestamp", time.time()),
            ttl=d.get("ttl", 86400),
            replication_factor=d.get("replication_factor", 3),
            is_permanent=d.get("is_permanent", False),
            source_peer_id=d.get("source_peer_id", ""),
        )


@dataclass
class ShardResponsibility:
    """Tracks which shards this node is responsible for."""
    geohash_prefix: str
    data_types: list[DataType]
    peer_count: int = 0  # How many peers share this shard
    last_sync: float = 0


class DHTRouter:
    """
    Routes data to appropriate nodes based on DHT keyspace.
    
    Uses Kademlia-style XOR distance for routing decisions.
    """
    
    def __init__(self, node_id: str):
        self._node_id = node_id
        self._node_id_int = int(hashlib.sha256(node_id.encode()).hexdigest(), 16)
    
    def get_distance(self, key: str) -> int:
        """Calculate XOR distance between this node and a key."""
        key_int = int(hashlib.sha256(key.encode()).hexdigest(), 16)
        return self._node_id_int ^ key_int
    
    def should_store(self, shard_key: str, total_nodes: int, replication: int = 3) -> bool:
        """
        Determine if this node should store data for a shard.
        
        Based on consistent hashing - each node stores data for nearby keys.
        """
        if total_nodes <= replication:
            return True  # Small network - everyone stores everything
        
        distance = self.get_distance(shard_key)
        # Node stores if it's in the closest N nodes (by XOR distance)
        # Approximation: store if distance is in bottom replication/total_nodes fraction
        threshold = (2**256) * replication // max(total_nodes, 1)
        return distance < threshold
    
    def get_responsible_nodes(
        self, 
        shard_key: str, 
        all_peers: list[tuple[str, str]],  # (peer_id, address)
        replication: int = 3
    ) -> list[tuple[str, str]]:
        """Get the nodes responsible for storing a shard key."""
        if not all_peers:
            return []
        
        # Sort peers by XOR distance to the shard key
        key_int = int(hashlib.sha256(shard_key.encode()).hexdigest(), 16)
        
        def peer_distance(peer: tuple[str, str]) -> int:
            peer_int = int(hashlib.sha256(peer[0].encode()).hexdigest(), 16)
            return peer_int ^ key_int
        
        sorted_peers = sorted(all_peers, key=peer_distance)
        return sorted_peers[:replication]


class ShardedStorage:
    """
    Distributed storage with geographic sharding.
    
    Data is partitioned by geohash so nodes only store data relevant to
    regions they're interested in (viewing on map, nearby, or responsible for).
    """
    
    def __init__(
        self,
        peer_id: str,
        my_geohash: str = "",
        on_data_received: Callable[[ShardedData], None] | None = None,
    ):
        self._peer_id = peer_id
        self._my_geohash = my_geohash
        self._on_data_received = on_data_received
        
        self._router = DHTRouter(peer_id)
        
        # Local storage - only data we're responsible for or interested in
        self._local_data: dict[str, ShardedData] = {}
        
        # Shards we're responsible for (based on DHT)
        self._my_shards: dict[str, ShardResponsibility] = {}
        
        # Shards we're viewing (loaded on-demand)
        self._viewed_shards: set[str] = set()
        
        # Permanent infrastructure - always cached locally
        self._infrastructure_cache: dict[str, ShardedData] = {}
        
        # Peer addresses for routing
        self._peer_addresses: dict[str, str] = {}  # peer_id -> address
        
        # Stats
        self._stats = {
            "local_items": 0,
            "infrastructure_items": 0,
            "shards_responsible": 0,
            "shards_viewing": 0,
        }
    
    def set_my_location(self, lat: float, lon: float) -> None:
        """Set our location for shard responsibility."""
        self._my_geohash = encode_geohash(lat, lon, GEOHASH_PRECISION_LOCAL)
        self._update_shard_responsibility()
    
    def _update_shard_responsibility(self) -> None:
        """Update which shards we're responsible for based on location and DHT."""
        if not self._my_geohash:
            return
        
        # Always responsible for our local area
        local_prefix = self._my_geohash[:GEOHASH_PRECISION_REGION]
        self._my_shards[local_prefix] = ShardResponsibility(
            geohash_prefix=local_prefix,
            data_types=list(DataType),
        )
        
        # Also responsible for neighboring regions (geohash neighbors)
        for neighbor in get_geohash_neighbors(local_prefix):
            if neighbor not in self._my_shards:
                self._my_shards[neighbor] = ShardResponsibility(
                    geohash_prefix=neighbor,
                    data_types=[DataType.INFRASTRUCTURE, DataType.CELL_TOWER],
                )
        
        self._stats["shards_responsible"] = len(self._my_shards)
    
    def update_peers(self, peers: dict[str, str]) -> None:
        """Update known peer addresses."""
        self._peer_addresses = peers
    
    async def store(self, data: ShardedData) -> bool:
        """
        Store data locally if we're responsible for it.
        
        Returns True if stored locally, False if routed elsewhere.
        """
        # Always store permanent infrastructure locally
        if data.is_permanent or data.data_type in (DataType.INFRASTRUCTURE, DataType.CELL_TOWER):
            self._infrastructure_cache[data.data_id] = data
            self._stats["infrastructure_items"] = len(self._infrastructure_cache)
            return True
        
        # Check if we should store based on DHT
        total_nodes = len(self._peer_addresses) + 1
        if self._router.should_store(data.shard_key, total_nodes, data.replication_factor):
            self._local_data[data.data_id] = data
            self._stats["local_items"] = len(self._local_data)
            
            if self._on_data_received:
                self._on_data_received(data)
            return True
        
        return False
    
    async def store_and_replicate(
        self,
        data: ShardedData,
        session: aiohttp.ClientSession | None = None,
    ) -> int:
        """Store data locally and replicate to responsible nodes."""
        stored_count = 0
        
        # Store locally first
        if await self.store(data):
            stored_count += 1
        
        # Find nodes responsible for this shard
        all_peers = [(pid, addr) for pid, addr in self._peer_addresses.items()]
        responsible = self._router.get_responsible_nodes(
            data.shard_key, all_peers, data.replication_factor
        )
        
        if not responsible:
            return stored_count
        
        # Replicate to responsible nodes
        close_session = session is None
        if session is None:
            session = aiohttp.ClientSession()
        
        try:
            for peer_id, address in responsible:
                if peer_id == self._peer_id:
                    continue  # Skip self
                try:
                    url = f"http://{address}/p2p/shard/store"
                    async with session.post(
                        url,
                        json={"data": data.to_dict()},
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as response:
                        if response.status == 200:
                            stored_count += 1
                except Exception as e:
                    _LOGGER.debug("Failed to replicate to %s: %s", address, e)
        finally:
            if close_session:
                await session.close()
        
        return stored_count
    
    async def get(self, data_id: str) -> ShardedData | None:
        """Get data by ID - check local storage first."""
        # Check infrastructure cache
        if data_id in self._infrastructure_cache:
            return self._infrastructure_cache[data_id]
        
        # Check local storage
        if data_id in self._local_data:
            data = self._local_data[data_id]
            if not data.is_expired:
                return data
            else:
                del self._local_data[data_id]
        
        return None
    
    async def get_by_geohash(
        self,
        geohash_prefix: str,
        data_type: DataType | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> list[ShardedData]:
        """
        Get all data for a geographic region.
        
        Loads from local storage and fetches from network if needed.
        """
        results: list[ShardedData] = []
        
        # Check local data
        for data in list(self._local_data.values()):
            if data.is_expired:
                del self._local_data[data.data_id]
                continue
            if data.geohash.startswith(geohash_prefix):
                if data_type is None or data.data_type == data_type:
                    results.append(data)
        
        # Check infrastructure cache
        for data in self._infrastructure_cache.values():
            if data.geohash.startswith(geohash_prefix):
                if data_type is None or data.data_type == data_type:
                    if data.data_id not in {r.data_id for r in results}:
                        results.append(data)
        
        # Mark this shard as being viewed
        self._viewed_shards.add(geohash_prefix)
        self._stats["shards_viewing"] = len(self._viewed_shards)
        
        # If we don't have much data, try to fetch from network
        if len(results) < 10 and self._peer_addresses:
            fetched = await self._fetch_from_network(geohash_prefix, data_type, session)
            for data in fetched:
                if data.data_id not in {r.data_id for r in results}:
                    results.append(data)
                    await self.store(data)
        
        return results
    
    async def _fetch_from_network(
        self,
        geohash_prefix: str,
        data_type: DataType | None,
        session: aiohttp.ClientSession | None = None,
    ) -> list[ShardedData]:
        """Fetch data for a region from the network."""
        results: list[ShardedData] = []
        
        shard_key = f"{geohash_prefix}:{data_type.value if data_type else 'all'}"
        all_peers = [(pid, addr) for pid, addr in self._peer_addresses.items()]
        responsible = self._router.get_responsible_nodes(shard_key, all_peers, 3)
        
        if not responsible:
            return results
        
        close_session = session is None
        if session is None:
            session = aiohttp.ClientSession()
        
        try:
            for peer_id, address in responsible[:3]:  # Ask up to 3 peers
                try:
                    url = f"http://{address}/p2p/shard/query"
                    params = {"geohash": geohash_prefix}
                    if data_type:
                        params["type"] = data_type.value
                    
                    async with session.get(
                        url,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            for item in data.get("items", []):
                                results.append(ShardedData.from_dict(item))
                            if results:
                                break  # Got data from one peer
                except Exception as e:
                    _LOGGER.debug("Failed to fetch from %s: %s", address, e)
        finally:
            if close_session:
                await session.close()
        
        return results
    
    def get_all_infrastructure(self) -> list[ShardedData]:
        """Get all cached infrastructure (always available locally)."""
        return list(self._infrastructure_cache.values())
    
    def cleanup_expired(self) -> int:
        """Remove expired data. Returns count of removed items."""
        expired_ids = [
            data_id for data_id, data in self._local_data.items()
            if data.is_expired
        ]
        for data_id in expired_ids:
            del self._local_data[data_id]
        
        self._stats["local_items"] = len(self._local_data)
        return len(expired_ids)
    
    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        return {
            **self._stats,
            "my_geohash": self._my_geohash,
            "peer_count": len(self._peer_addresses),
        }


@dataclass
class NodeDecay:
    """
    Tracks node visibility decay.
    
    Nodes that disconnect don't immediately disappear - they fade over time.
    Infrastructure stays forever, regular peers decay after timeout.
    """
    peer_id: str
    last_seen: float
    decay_start: float | None = None  # When decay started (after disconnect)
    is_infrastructure: bool = False  # Datacenters, IXPs never decay
    
    # Decay settings
    DECAY_START_AFTER = 300  # Start decay 5 min after last seen
    FULL_DECAY_TIME = 3600  # Fully decay after 1 hour
    
    @property
    def decay_factor(self) -> float:
        """
        Get decay factor (1.0 = fully visible, 0.0 = invisible).
        
        Infrastructure never decays.
        """
        if self.is_infrastructure:
            return 1.0
        
        now = time.time()
        time_since_seen = now - self.last_seen
        
        if time_since_seen < self.DECAY_START_AFTER:
            return 1.0  # Recently seen - fully visible
        
        # Linear decay
        decay_progress = (time_since_seen - self.DECAY_START_AFTER) / self.FULL_DECAY_TIME
        return max(0.0, 1.0 - decay_progress)
    
    @property
    def should_remove(self) -> bool:
        """Check if node should be removed from view."""
        return self.decay_factor <= 0.0


class NodeDecayManager:
    """Manages decay for all nodes in the network."""
    
    def __init__(self):
        self._nodes: dict[str, NodeDecay] = {}
    
    def update_node(self, peer_id: str, is_infrastructure: bool = False) -> None:
        """Update a node's last seen time."""
        if peer_id in self._nodes:
            self._nodes[peer_id].last_seen = time.time()
            self._nodes[peer_id].decay_start = None
        else:
            self._nodes[peer_id] = NodeDecay(
                peer_id=peer_id,
                last_seen=time.time(),
                is_infrastructure=is_infrastructure,
            )
    
    def mark_infrastructure(self, peer_id: str) -> None:
        """Mark a node as infrastructure (never decays)."""
        if peer_id in self._nodes:
            self._nodes[peer_id].is_infrastructure = True
    
    def get_visible_nodes(self) -> list[tuple[str, float]]:
        """Get all visible nodes with their decay factors."""
        visible = []
        to_remove = []
        
        for peer_id, node in self._nodes.items():
            if node.should_remove:
                to_remove.append(peer_id)
            else:
                visible.append((peer_id, node.decay_factor))
        
        # Clean up fully decayed nodes
        for peer_id in to_remove:
            del self._nodes[peer_id]
        
        return visible
    
    def get_decay_factor(self, peer_id: str) -> float:
        """Get decay factor for a specific node."""
        if peer_id in self._nodes:
            return self._nodes[peer_id].decay_factor
        return 0.0


# === Geohash utilities ===

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def encode_geohash(lat: float, lon: float, precision: int = 5) -> str:
    """Encode lat/lon to geohash string."""
    lat_range = (-90.0, 90.0)
    lon_range = (-180.0, 180.0)
    
    geohash = []
    bits = 0
    bit_count = 0
    is_lon = True
    
    while len(geohash) < precision:
        if is_lon:
            mid = (lon_range[0] + lon_range[1]) / 2
            if lon >= mid:
                bits = (bits << 1) | 1
                lon_range = (mid, lon_range[1])
            else:
                bits = bits << 1
                lon_range = (lon_range[0], mid)
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                bits = (bits << 1) | 1
                lat_range = (mid, lat_range[1])
            else:
                bits = bits << 1
                lat_range = (lat_range[0], mid)
        
        is_lon = not is_lon
        bit_count += 1
        
        if bit_count == 5:
            geohash.append(BASE32[bits])
            bits = 0
            bit_count = 0
    
    return "".join(geohash)


def decode_geohash(geohash: str) -> tuple[float, float]:
    """Decode geohash to lat/lon (center of cell)."""
    lat_range = (-90.0, 90.0)
    lon_range = (-180.0, 180.0)
    is_lon = True
    
    for char in geohash:
        idx = BASE32.index(char.lower())
        for i in range(4, -1, -1):
            bit = (idx >> i) & 1
            if is_lon:
                mid = (lon_range[0] + lon_range[1]) / 2
                if bit:
                    lon_range = (mid, lon_range[1])
                else:
                    lon_range = (lon_range[0], mid)
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if bit:
                    lat_range = (mid, lat_range[1])
                else:
                    lat_range = (lat_range[0], mid)
            is_lon = not is_lon
    
    lat = (lat_range[0] + lat_range[1]) / 2
    lon = (lon_range[0] + lon_range[1]) / 2
    return lat, lon


def get_geohash_neighbors(geohash: str) -> list[str]:
    """Get the 8 neighboring geohash cells."""
    lat, lon = decode_geohash(geohash)
    precision = len(geohash)
    
    # Approximate cell size
    lat_delta = 180.0 / (2 ** (precision * 5 // 2))
    lon_delta = 360.0 / (2 ** ((precision * 5 + 1) // 2))
    
    neighbors = []
    for dlat in [-lat_delta, 0, lat_delta]:
        for dlon in [-lon_delta, 0, lon_delta]:
            if dlat == 0 and dlon == 0:
                continue
            nlat = lat + dlat
            nlon = lon + dlon
            # Wrap longitude
            if nlon > 180:
                nlon -= 360
            elif nlon < -180:
                nlon += 360
            # Clamp latitude
            nlat = max(-90, min(90, nlat))
            neighbors.append(encode_geohash(nlat, nlon, precision))
    
    return neighbors
