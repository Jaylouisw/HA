"""
P2P Discovery and Communication for HAM Network.

Implements a distributed peer-to-peer network with no central server dependency.
Uses gossip protocol for peer discovery and DHT-like storage for topology data.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Any, Callable

import aiohttp
from aiohttp import web

from .const import (
    DOMAIN,
    P2P_PROTOCOL_VERSION,
    P2P_MAX_PEERS,
    P2P_PEER_TIMEOUT,
    P2P_GOSSIP_INTERVAL,
    P2P_DHT_REPLICATION,
    DEFAULT_PEER_PORT,
    EVENT_PEER_DISCOVERED,
    EVENT_PEER_LOST,
)

_LOGGER = logging.getLogger(__name__)


class MessageType(IntEnum):
    """P2P message types."""
    PING = 1
    PONG = 2
    PEER_ANNOUNCE = 3
    PEER_REQUEST = 4
    PEER_LIST = 5
    TOPOLOGY_UPDATE = 6
    TOPOLOGY_REQUEST = 7
    TOPOLOGY_RESPONSE = 8
    LEADERBOARD_UPDATE = 9
    LEADERBOARD_REQUEST = 10
    LEADERBOARD_RESPONSE = 11
    TRACEROUTE_RESULT = 12
    PRIVACY_PROOF = 13  # Prove contribution without revealing identity


@dataclass
class P2PPeer:
    """Represents a peer in the P2P network."""
    
    peer_id: str
    host: str
    port: int
    display_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    last_seen: datetime = field(default_factory=datetime.now)
    is_online: bool = True
    protocol_version: str = P2P_PROTOCOL_VERSION
    contribution_proof: str | None = None  # Proof they're contributing
    
    # Stats
    uptime_seconds: int = 0
    traceroute_count: int = 0
    total_hops: int = 0
    peers_discovered: int = 0
    
    @property
    def address(self) -> str:
        """Get peer address."""
        return f"{self.host}:{self.port}"
    
    @property
    def is_stale(self) -> bool:
        """Check if peer is stale (no recent contact)."""
        return (datetime.now() - self.last_seen).total_seconds() > P2P_PEER_TIMEOUT
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "peer_id": self.peer_id,
            "host": self.host,
            "port": self.port,
            "display_name": self.display_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "last_seen": self.last_seen.isoformat(),
            "is_online": self.is_online,
            "protocol_version": self.protocol_version,
            "contribution_proof": self.contribution_proof,
            "uptime_seconds": self.uptime_seconds,
            "traceroute_count": self.traceroute_count,
            "total_hops": self.total_hops,
            "peers_discovered": self.peers_discovered,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> P2PPeer:
        """Create from dictionary."""
        last_seen = datetime.now()
        if data.get("last_seen"):
            try:
                last_seen = datetime.fromisoformat(data["last_seen"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            peer_id=data["peer_id"],
            host=data["host"],
            port=data.get("port", DEFAULT_PEER_PORT),
            display_name=data.get("display_name"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            last_seen=last_seen,
            is_online=data.get("is_online", True),
            protocol_version=data.get("protocol_version", P2P_PROTOCOL_VERSION),
            contribution_proof=data.get("contribution_proof"),
            uptime_seconds=data.get("uptime_seconds", 0),
            traceroute_count=data.get("traceroute_count", 0),
            total_hops=data.get("total_hops", 0),
            peers_discovered=data.get("peers_discovered", 0),
        )


class ContributionProof:
    """
    Generates and verifies contribution proofs.
    
    Proves a peer is contributing without revealing their identity.
    Uses a simple hash-based proof system.
    """
    
    @staticmethod
    def generate(peer_id: str, contribution_data: dict[str, Any]) -> str:
        """Generate a contribution proof."""
        # Create proof from contribution metrics
        proof_data = {
            "peer_id_hash": hashlib.sha256(peer_id.encode()).hexdigest()[:16],
            "traceroutes": contribution_data.get("traceroute_count", 0),
            "uptime_hours": contribution_data.get("uptime_seconds", 0) // 3600,
            "timestamp": int(time.time()),
            "nonce": secrets.token_hex(8),
        }
        
        proof_string = json.dumps(proof_data, sort_keys=True)
        signature = hashlib.sha256(proof_string.encode()).hexdigest()[:32]
        
        return f"{proof_string}|{signature}"
    
    @staticmethod
    def verify(proof: str) -> tuple[bool, dict[str, Any] | None]:
        """
        Verify a contribution proof.
        
        Returns (is_valid, proof_data).
        """
        try:
            proof_string, signature = proof.rsplit("|", 1)
            expected_sig = hashlib.sha256(proof_string.encode()).hexdigest()[:32]
            
            if signature != expected_sig:
                return False, None
            
            proof_data = json.loads(proof_string)
            
            # Check timestamp isn't too old (24 hours)
            if time.time() - proof_data.get("timestamp", 0) > 86400:
                return False, None
            
            return True, proof_data
            
        except (ValueError, json.JSONDecodeError):
            return False, None
    
    @staticmethod
    def is_contributing(proof: str, min_traceroutes: int = 1) -> bool:
        """Check if proof shows meaningful contribution."""
        is_valid, data = ContributionProof.verify(proof)
        if not is_valid or not data:
            return False
        
        return data.get("traceroutes", 0) >= min_traceroutes


class P2PNode:
    """
    P2P Node for HAM Network.
    
    Handles peer discovery, gossip protocol, and distributed data storage.
    
    Port Handling:
    - Pass port=0 to auto-assign an available port (recommended)
    - The actual port is available via .port property after start()
    - Each peer tracks its own port and shares it during discovery
    """
    
    def __init__(
        self,
        peer_id: str,
        host: str,
        port: int = 0,  # 0 = auto-assign
        display_name: str = "",
        on_peer_discovered: Callable[[P2PPeer], None] | None = None,
        on_peer_lost: Callable[[str], None] | None = None,
        on_topology_update: Callable[[dict], None] | None = None,
    ):
        """Initialize P2P node. Use port=0 for auto-assignment."""
        self._peer_id = peer_id
        self._host = host
        self._requested_port = port
        self._actual_port: int = 0  # Set after server starts
        self._display_name = display_name
        
        # Callbacks
        self._on_peer_discovered = on_peer_discovered
        self._on_peer_lost = on_peer_lost
        self._on_topology_update = on_topology_update
        
        # Peer management
        self._peers: dict[str, P2PPeer] = {}
        self._bootstrap_peers: list[str] = []
        
        # Local data
        self._my_location: tuple[float, float] | None = None
        self._my_stats: dict[str, Any] = {
            "uptime_seconds": 0,
            "traceroute_count": 0,
            "total_hops": 0,
            "peers_discovered": 0,
            "start_time": time.time(),
        }
        
        # Network topology storage (DHT-like)
        self._topology_data: dict[str, Any] = {"peers": [], "links": []}
        self._leaderboard_data: list[dict[str, Any]] = []
        
        # Server
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._server: web.TCPSite | None = None
        
        # Background tasks
        self._tasks: list[asyncio.Task] = []
        self._running = False
    
    @property
    def port(self) -> int:
        """Get the actual port (after start)."""
        return self._actual_port or self._requested_port
    
    async def start(self, bootstrap_peers: list[str] | None = None) -> None:
        """Start the P2P node."""
        self._bootstrap_peers = bootstrap_peers or []
        self._running = True
        
        # Start HTTP server for P2P communication
        await self._start_server()
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._gossip_loop()),
            asyncio.create_task(self._peer_maintenance_loop()),
            asyncio.create_task(self._stats_update_loop()),
        ]
        
        # Bootstrap: connect to known peers
        if self._bootstrap_peers:
            await self._bootstrap()
        
        _LOGGER.info("P2P node started on %s:%s", self._host, self._actual_port)
    
    async def stop(self) -> None:
        """Stop the P2P node."""
        self._running = False
        
        # Cancel background tasks
        for task in self._tasks:
            task.cancel()
        
        # Stop server
        if self._runner:
            await self._runner.cleanup()
        
        _LOGGER.info("P2P node stopped")
    
    async def _start_server(self) -> None:
        """Start the HTTP server for P2P communication."""
        self._app = web.Application()
        self._app.router.add_post("/p2p/ping", self._handle_ping)
        self._app.router.add_post("/p2p/announce", self._handle_announce)
        self._app.router.add_get("/p2p/peers", self._handle_get_peers)
        self._app.router.add_post("/p2p/topology", self._handle_topology_update)
        self._app.router.add_get("/p2p/topology", self._handle_get_topology)
        self._app.router.add_post("/p2p/leaderboard", self._handle_leaderboard_update)
        self._app.router.add_get("/p2p/leaderboard", self._handle_get_leaderboard)
        self._app.router.add_post("/p2p/traceroute", self._handle_traceroute_result)
        
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        
        # Bind to requested port (0 = auto-assign)
        self._server = web.TCPSite(self._runner, "0.0.0.0", self._requested_port)
        await self._server.start()
        
        # Get actual assigned port
        # The server's _server attribute contains the actual socket
        if self._server._server and self._server._server.sockets:
            self._actual_port = self._server._server.sockets[0].getsockname()[1]
        else:
            self._actual_port = self._requested_port
        
        _LOGGER.debug("P2P HTTP server listening on port %d", self._actual_port)
    
    # === HTTP Handlers ===
    
    async def _handle_ping(self, request: web.Request) -> web.Response:
        """Handle ping request."""
        data = await request.json()
        
        # Update peer info
        if "peer_id" in data:
            await self._update_peer(data)
        
        return web.json_response({
            "peer_id": self._peer_id,
            "protocol_version": P2P_PROTOCOL_VERSION,
            "timestamp": time.time(),
        })
    
    async def _handle_announce(self, request: web.Request) -> web.Response:
        """Handle peer announcement."""
        data = await request.json()
        
        if "peer_id" not in data:
            return web.json_response({"error": "Missing peer_id"}, status=400)
        
        # Verify contribution proof if provided
        contribution_verified = False
        if data.get("contribution_proof"):
            contribution_verified = ContributionProof.is_contributing(data["contribution_proof"])
        
        # Update peer
        await self._update_peer(data, contribution_verified)
        
        return web.json_response({
            "peer_id": self._peer_id,
            "accepted": True,
            "peer_count": len(self._peers),
        })
    
    async def _handle_get_peers(self, request: web.Request) -> web.Response:
        """Handle request for peer list."""
        # Only return peers to those who are contributing
        proof = request.headers.get("X-Contribution-Proof", "")
        
        if not ContributionProof.is_contributing(proof):
            # Return limited info
            return web.json_response({
                "peer_count": len(self._peers),
                "message": "Contribute to see full peer list",
            })
        
        # Return full peer list
        peers = [p.to_dict() for p in self._peers.values() if not p.is_stale]
        return web.json_response({"peers": peers})
    
    async def _handle_topology_update(self, request: web.Request) -> web.Response:
        """Handle topology update from peer."""
        data = await request.json()
        
        # Merge topology data
        if "links" in data:
            self._merge_topology_links(data["links"])
        
        if self._on_topology_update:
            self._on_topology_update(self._topology_data)
        
        return web.json_response({"accepted": True})
    
    async def _handle_get_topology(self, request: web.Request) -> web.Response:
        """Handle request for topology data."""
        proof = request.headers.get("X-Contribution-Proof", "")
        
        if not ContributionProof.is_contributing(proof):
            return web.json_response({
                "message": "Contribute to see topology",
                "peer_count": len(self._peers),
            })
        
        return web.json_response(self._topology_data)
    
    async def _handle_leaderboard_update(self, request: web.Request) -> web.Response:
        """Handle leaderboard entry update."""
        data = await request.json()
        
        if "entry" in data:
            self._update_leaderboard_entry(data["entry"])
        
        return web.json_response({"accepted": True})
    
    async def _handle_get_leaderboard(self, request: web.Request) -> web.Response:
        """Handle request for leaderboard."""
        return web.json_response({"leaderboard": self._leaderboard_data})
    
    async def _handle_traceroute_result(self, request: web.Request) -> web.Response:
        """Handle traceroute result submission."""
        data = await request.json()
        
        if "traceroute" in data:
            # Add to topology
            self._add_traceroute_to_topology(data)
        
        return web.json_response({"accepted": True})
    
    # === Peer Management ===
    
    async def _update_peer(self, data: dict[str, Any], contribution_verified: bool = False) -> None:
        """Update or add a peer."""
        peer_id = data["peer_id"]
        
        if peer_id == self._peer_id:
            return  # Don't add ourselves
        
        is_new = peer_id not in self._peers
        
        if is_new:
            peer = P2PPeer.from_dict(data)
            if contribution_verified:
                peer.contribution_proof = data.get("contribution_proof")
            self._peers[peer_id] = peer
            
            self._my_stats["peers_discovered"] += 1
            
            if self._on_peer_discovered:
                self._on_peer_discovered(peer)
            
            _LOGGER.info("New peer discovered: %s", peer.display_name or peer_id)
        else:
            # Update existing peer
            peer = self._peers[peer_id]
            peer.last_seen = datetime.now()
            peer.is_online = True
            
            if data.get("display_name"):
                peer.display_name = data["display_name"]
            if data.get("latitude") is not None:
                peer.latitude = data["latitude"]
            if data.get("longitude") is not None:
                peer.longitude = data["longitude"]
            if contribution_verified:
                peer.contribution_proof = data.get("contribution_proof")
            
            # Update stats
            for stat in ["uptime_seconds", "traceroute_count", "total_hops", "peers_discovered"]:
                if stat in data:
                    setattr(peer, stat, data[stat])
    
    async def _remove_stale_peers(self) -> None:
        """Remove peers that haven't been seen recently."""
        stale_peers = [pid for pid, p in self._peers.items() if p.is_stale]
        
        for peer_id in stale_peers:
            peer = self._peers.pop(peer_id, None)
            if peer and self._on_peer_lost:
                self._on_peer_lost(peer_id)
            _LOGGER.info("Peer went offline: %s", peer.display_name if peer else peer_id)
    
    # === Gossip Protocol ===
    
    async def _gossip_loop(self) -> None:
        """Background task for gossip protocol."""
        while self._running:
            try:
                await asyncio.sleep(P2P_GOSSIP_INTERVAL)
                await self._gossip()
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error("Gossip error: %s", e)
    
    async def _gossip(self) -> None:
        """Perform gossip round - share our info and get peer info."""
        if not self._peers:
            return
        
        # Select random peers to gossip with
        peers_to_contact = list(self._peers.values())[:min(5, len(self._peers))]
        
        my_data = self._get_my_announcement()
        
        async with aiohttp.ClientSession() as session:
            for peer in peers_to_contact:
                try:
                    url = f"http://{peer.address}/p2p/announce"
                    async with session.post(
                        url,
                        json=my_data,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            peer.last_seen = datetime.now()
                            peer.is_online = True
                            
                            # Request their peer list
                            await self._request_peers(session, peer)
                except Exception as e:
                    _LOGGER.debug("Failed to gossip with %s: %s", peer.address, e)
    
    async def _request_peers(self, session: aiohttp.ClientSession, peer: P2PPeer) -> None:
        """Request peer list from another peer."""
        try:
            url = f"http://{peer.address}/p2p/peers"
            proof = self._generate_contribution_proof()
            
            async with session.get(
                url,
                headers={"X-Contribution-Proof": proof},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    for peer_data in data.get("peers", []):
                        await self._update_peer(peer_data)
        except Exception as e:
            _LOGGER.debug("Failed to get peers from %s: %s", peer.address, e)
    
    async def _bootstrap(self) -> None:
        """Connect to bootstrap peers."""
        async with aiohttp.ClientSession() as session:
            for peer_addr in self._bootstrap_peers:
                try:
                    url = f"http://{peer_addr}/p2p/announce"
                    async with session.post(
                        url,
                        json=self._get_my_announcement(),
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            _LOGGER.info("Connected to bootstrap peer: %s", peer_addr)
                            
                            # Get their peer list
                            host, port = peer_addr.rsplit(":", 1)
                            temp_peer = P2PPeer(
                                peer_id="bootstrap",
                                host=host,
                                port=int(port)
                            )
                            await self._request_peers(session, temp_peer)
                except Exception as e:
                    _LOGGER.warning("Failed to connect to bootstrap peer %s: %s", peer_addr, e)
    
    async def add_bootstrap_peer(self, peer_addr: str) -> bool:
        """Add and connect to a new bootstrap peer dynamically.
        
        Called when auto-discovery finds new peers after initial startup.
        Returns True if successfully connected.
        """
        if peer_addr in self._bootstrap_peers:
            return True  # Already known
        
        self._bootstrap_peers.append(peer_addr)
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://{peer_addr}/p2p/announce"
                async with session.post(
                    url,
                    json=self._get_my_announcement(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        _LOGGER.info("Connected to newly discovered peer: %s", peer_addr)
                        
                        # Get their peer list
                        host, port = peer_addr.rsplit(":", 1)
                        temp_peer = P2PPeer(
                            peer_id="discovered",
                            host=host,
                            port=int(port)
                        )
                        await self._request_peers(session, temp_peer)
                        return True
        except Exception as e:
            _LOGGER.debug("Failed to connect to discovered peer %s: %s", peer_addr, e)
        
        return False
    
    async def _peer_maintenance_loop(self) -> None:
        """Background task for peer maintenance."""
        while self._running:
            try:
                await asyncio.sleep(60)
                await self._remove_stale_peers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error("Peer maintenance error: %s", e)
    
    async def _stats_update_loop(self) -> None:
        """Background task for updating stats."""
        while self._running:
            try:
                await asyncio.sleep(60)
                self._my_stats["uptime_seconds"] = int(time.time() - self._my_stats["start_time"])
            except asyncio.CancelledError:
                break
    
    # === Helpers ===
    
    def _get_my_announcement(self) -> dict[str, Any]:
        """Get our announcement data."""
        data = {
            "peer_id": self._peer_id,
            "host": self._host,
            "port": self._actual_port,  # Use actual assigned port
            "display_name": self._display_name,
            "protocol_version": P2P_PROTOCOL_VERSION,
            "contribution_proof": self._generate_contribution_proof(),
            **self._my_stats,
        }
        
        if self._my_location:
            data["latitude"], data["longitude"] = self._my_location
        
        return data
    
    def _generate_contribution_proof(self) -> str:
        """Generate contribution proof."""
        return ContributionProof.generate(self._peer_id, self._my_stats)
    
    def _merge_topology_links(self, links: list[dict]) -> None:
        """Merge incoming topology links with our data."""
        existing = {(l["source"], l["target"]) for l in self._topology_data.get("links", [])}
        
        for link in links:
            key = (link.get("source"), link.get("target"))
            if key not in existing:
                self._topology_data.setdefault("links", []).append(link)
                existing.add(key)
    
    def _update_leaderboard_entry(self, entry: dict[str, Any]) -> None:
        """Update a leaderboard entry."""
        peer_id = entry.get("peer_id")
        if not peer_id:
            return
        
        # Remove old entry
        self._leaderboard_data = [e for e in self._leaderboard_data if e.get("peer_id") != peer_id]
        
        # Add new entry
        self._leaderboard_data.append(entry)
        
        # Sort by contribution score
        self._leaderboard_data.sort(
            key=lambda x: x.get("contribution_score", 0),
            reverse=True
        )
        
        # Keep top 100
        self._leaderboard_data = self._leaderboard_data[:100]
    
    def _add_traceroute_to_topology(self, data: dict[str, Any]) -> None:
        """Add traceroute result to topology."""
        traceroute = data.get("traceroute", {})
        source = data.get("source_peer_id")
        target = data.get("target_peer_id")
        
        if not source or not target:
            return
        
        link = {
            "source": source,
            "target": target,
            "latency_ms": traceroute.get("total_time_ms"),
            "hop_count": len(traceroute.get("hops", [])),
            "hops": traceroute.get("hops", []),
            "timestamp": traceroute.get("timestamp"),
        }
        
        self._merge_topology_links([link])
        
        # Update stats
        self._my_stats["traceroute_count"] += 1
        self._my_stats["total_hops"] += len(traceroute.get("hops", []))
    
    # === Public API ===
    
    def set_location(self, lat: float, lon: float) -> None:
        """Set our location."""
        self._my_location = (lat, lon)
    
    def get_peers(self) -> list[P2PPeer]:
        """Get list of known peers."""
        return [p for p in self._peers.values() if not p.is_stale]
    
    def get_topology(self) -> dict[str, Any]:
        """Get topology data."""
        # Update peers in topology
        self._topology_data["peers"] = [
            p.to_dict() for p in self._peers.values() if not p.is_stale
        ]
        return self._topology_data
    
    def get_leaderboard(self) -> list[dict[str, Any]]:
        """Get leaderboard data."""
        return self._leaderboard_data
    
    def get_my_stats(self) -> dict[str, Any]:
        """Get our stats."""
        return self._my_stats.copy()
    
    async def submit_traceroute(self, target_peer_id: str, traceroute_data: dict) -> None:
        """Submit traceroute results to the network."""
        data = {
            "source_peer_id": self._peer_id,
            "target_peer_id": target_peer_id,
            "traceroute": traceroute_data,
        }
        
        # Add to our topology
        self._add_traceroute_to_topology(data)
        
        # Share with peers
        async with aiohttp.ClientSession() as session:
            for peer in list(self._peers.values())[:P2P_DHT_REPLICATION]:
                try:
                    url = f"http://{peer.address}/p2p/traceroute"
                    await session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=5))
                except Exception:
                    pass
    
    async def update_leaderboard(self, entry: dict[str, Any]) -> None:
        """Update our leaderboard entry."""
        self._update_leaderboard_entry(entry)
        
        # Share with peers
        async with aiohttp.ClientSession() as session:
            for peer in list(self._peers.values())[:P2P_DHT_REPLICATION]:
                try:
                    url = f"http://{peer.address}/p2p/leaderboard"
                    await session.post(
                        url,
                        json={"entry": entry},
                        timeout=aiohttp.ClientTimeout(total=5)
                    )
                except Exception:
                    pass
