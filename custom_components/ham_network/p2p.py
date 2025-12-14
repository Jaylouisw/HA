"""
P2P Discovery and Communication for HAM Network.

Implements a distributed peer-to-peer network with no central server dependency.
Uses gossip protocol for peer discovery and DHT-like storage for topology data.

Sharding Strategy:
- Data is partitioned geographically using geohash
- Each node stores data for its region + neighboring regions
- Infrastructure (datacenters, IXPs, cell towers) is replicated widely
- Transient data (traceroutes, peers) expires and loads on-demand
- Nodes that disconnect decay from view over time
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
from .sharding import (
    ShardedStorage,
    ShardedData,
    DataType,
    NodeDecayManager,
    encode_geohash,
    GEOHASH_PRECISION_REGION,
)
from .infrastructure_db import classify_infrastructure, detect_mobile_infrastructure

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
    # Live data sync
    FULL_SYNC_REQUEST = 14
    FULL_SYNC_RESPONSE = 15
    LIVE_UPDATE = 16
    MOBILE_TRACEROUTE = 17  # Mobile app traceroute back to home server


@dataclass
class SharedTraceroute:
    """
    Traceroute data shared across all nodes.
    
    Contains full hop details for accurate mapping including
    geolocation, ASN info, and infrastructure detection.
    """
    traceroute_id: str  # Unique ID for this traceroute
    source_peer_id: str
    source_display_name: str | None
    target_peer_id: str | None  # None if target is external (e.g., mobile)
    target_ip: str
    target_display_name: str | None
    timestamp: float
    hops: list[dict[str, Any]]  # Full enriched hop data
    total_time_ms: float | None
    success: bool
    path_summary: dict[str, Any] | None = None
    is_mobile: bool = False  # True if from mobile app
    carrier: str | None = None  # Mobile carrier name if detected
    cell_tower_info: dict[str, Any] | None = None  # Cell tower details if available
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "traceroute_id": self.traceroute_id,
            "source_peer_id": self.source_peer_id,
            "source_display_name": self.source_display_name,
            "target_peer_id": self.target_peer_id,
            "target_ip": self.target_ip,
            "target_display_name": self.target_display_name,
            "timestamp": self.timestamp,
            "hops": self.hops,
            "total_time_ms": self.total_time_ms,
            "success": self.success,
            "path_summary": self.path_summary,
            "is_mobile": self.is_mobile,
            "carrier": self.carrier,
            "cell_tower_info": self.cell_tower_info,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SharedTraceroute:
        """Create from dictionary."""
        return cls(
            traceroute_id=data.get("traceroute_id", secrets.token_hex(8)),
            source_peer_id=data["source_peer_id"],
            source_display_name=data.get("source_display_name"),
            target_peer_id=data.get("target_peer_id"),
            target_ip=data.get("target_ip", ""),
            target_display_name=data.get("target_display_name"),
            timestamp=data.get("timestamp", time.time()),
            hops=data.get("hops", []),
            total_time_ms=data.get("total_time_ms"),
            success=data.get("success", False),
            path_summary=data.get("path_summary"),
            is_mobile=data.get("is_mobile", False),
            carrier=data.get("carrier"),
            cell_tower_info=data.get("cell_tower_info"),
        )


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
    
    Sharding:
    - Uses DHT-based sharding for scalable storage
    - Each node stores data for its geographic region
    - Infrastructure (permanent) is replicated more widely
    - Transient data loads on-demand from nearby nodes
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
        on_traceroute_received: Callable[[SharedTraceroute], None] | None = None,
        share_data: bool = False,  # PRIVACY: Disabled by default
    ):
        """Initialize P2P node. Use port=0 for auto-assignment."""
        self._peer_id = peer_id
        self._host = host
        self._requested_port = port
        self._actual_port: int = 0  # Set after server starts
        self._display_name = display_name
        
        # Privacy: Data sharing disabled by default
        self._share_data = share_data
        
        # Callbacks
        self._on_peer_discovered = on_peer_discovered
        self._on_peer_lost = on_peer_lost
        self._on_topology_update = on_topology_update
        self._on_traceroute_received = on_traceroute_received
        
        # Peer management
        self._peers: dict[str, P2PPeer] = {}
        self._bootstrap_peers: list[str] = []
        
        # Local data
        self._my_location: tuple[float, float] | None = None
        self._my_geohash: str = ""
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
        
        # Sharded storage for scalable data management
        self._sharded_storage = ShardedStorage(
            peer_id=peer_id,
            on_data_received=self._on_sharded_data_received,
        )
        
        # Node decay manager - handles visibility decay of disconnected nodes
        self._decay_manager = NodeDecayManager()
        
        # Shared traceroute data - all traceroutes from all nodes
        self._shared_traceroutes: dict[str, SharedTraceroute] = {}
        self._traceroute_max_age = 86400  # Keep traceroutes for 24 hours
        
        # Mobile app tokens (for receiving traceroutes from mobile devices)
        self._mobile_tokens: dict[str, dict[str, Any]] = {}  # token -> {peer_id, created, expires}
        
        # WebSocket connections for live updates
        self._ws_clients: list[web.WebSocketResponse] = []
        
        # Currently viewed map region (for on-demand loading)
        self._viewed_geohashes: set[str] = set()
        
        # Server
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._server: web.TCPSite | None = None
        
        # Background tasks
        self._tasks: list[asyncio.Task] = []
        self._running = False
    
    def _on_sharded_data_received(self, data: ShardedData) -> None:
        """Handle new data received from sharded storage."""
        if data.data_type == DataType.TRACEROUTE:
            # Convert to SharedTraceroute for compatibility
            tr = SharedTraceroute.from_dict(data.data)
            self._shared_traceroutes[tr.traceroute_id] = tr
            if self._on_traceroute_received:
                self._on_traceroute_received(tr)
    
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
            asyncio.create_task(self._data_sync_loop()),  # Periodic full sync
        ]
        
        # Bootstrap: connect to known peers
        if self._bootstrap_peers:
            await self._bootstrap()
        
        _LOGGER.info("P2P node started on %s:%s (sharing: %s)", 
                     self._host, self._actual_port, "enabled" if self._share_data else "disabled")
    
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
        
        # New routes for live data sync
        self._app.router.add_get("/p2p/sync", self._handle_full_sync)  # Get all traceroute data
        self._app.router.add_post("/p2p/broadcast", self._handle_broadcast)  # Receive live updates
        self._app.router.add_get("/p2p/ws", self._handle_websocket)  # WebSocket for live updates
        
        # Sharded storage routes (DHT-based)
        self._app.router.add_post("/p2p/shard/store", self._handle_shard_store)
        self._app.router.add_get("/p2p/shard/query", self._handle_shard_query)
        self._app.router.add_get("/p2p/shard/region", self._handle_shard_region)  # Load region data
        
        # Mobile app API routes
        self._app.router.add_post("/api/mobile/register", self._handle_mobile_register)
        self._app.router.add_post("/api/mobile/traceroute", self._handle_mobile_traceroute)
        self._app.router.add_get("/api/mobile/status", self._handle_mobile_status)
        
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
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
            
            # Also add to shared traceroutes for live sync
            if self._share_data:
                traceroute = SharedTraceroute.from_dict({
                    "source_peer_id": data.get("source_peer_id", ""),
                    "source_display_name": data.get("source_display_name"),
                    "target_peer_id": data.get("target_peer_id"),
                    "target_ip": data.get("traceroute", {}).get("target", ""),
                    "target_display_name": data.get("target_display_name"),
                    "hops": data.get("traceroute", {}).get("hops", []),
                    "total_time_ms": data.get("traceroute", {}).get("total_time_ms"),
                    "success": data.get("traceroute", {}).get("success", False),
                    "path_summary": data.get("traceroute", {}).get("path_summary"),
                })
                await self._store_and_broadcast_traceroute(traceroute)
        
        return web.json_response({"accepted": True})
    
    # === Live Data Sync Handlers ===
    
    async def _handle_full_sync(self, request: web.Request) -> web.Response:
        """Handle full sync request - return all shared traceroute data."""
        proof = request.headers.get("X-Contribution-Proof", "")
        
        if not ContributionProof.is_contributing(proof):
            return web.json_response({
                "message": "Contribute to access shared data",
                "traceroute_count": len(self._shared_traceroutes),
            })
        
        # Clean up old traceroutes first
        self._cleanup_old_traceroutes()
        
        return web.json_response({
            "traceroutes": [t.to_dict() for t in self._shared_traceroutes.values()],
            "peer_count": len(self._peers),
            "timestamp": time.time(),
        })
    
    async def _handle_broadcast(self, request: web.Request) -> web.Response:
        """Handle incoming broadcast of new traceroute data."""
        data = await request.json()
        
        if not self._share_data:
            return web.json_response({"accepted": False, "reason": "sharing_disabled"})
        
        if "traceroute" in data:
            traceroute = SharedTraceroute.from_dict(data["traceroute"])
            
            # Store locally
            self._shared_traceroutes[traceroute.traceroute_id] = traceroute
            
            # Notify callback
            if self._on_traceroute_received:
                self._on_traceroute_received(traceroute)
            
            # Push to WebSocket clients
            await self._broadcast_to_ws_clients({
                "type": "traceroute",
                "data": traceroute.to_dict(),
            })
        
        return web.json_response({"accepted": True})
    
    async def _handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connection for live updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Check contribution proof from query param
        proof = request.query.get("proof", "")
        if not ContributionProof.is_contributing(proof):
            await ws.send_json({"error": "Contribute to receive live updates"})
            await ws.close()
            return ws
        
        self._ws_clients.append(ws)
        _LOGGER.info("WebSocket client connected (total: %d)", len(self._ws_clients))
        
        try:
            # Send initial data
            await ws.send_json({
                "type": "initial",
                "traceroutes": [t.to_dict() for t in self._shared_traceroutes.values()],
                "peers": [p.to_dict() for p in self._peers.values() if not p.is_stale],
            })
            
            # Keep connection alive and handle messages
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("type") == "ping":
                        await ws.send_json({"type": "pong", "timestamp": time.time()})
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.warning("WebSocket error: %s", ws.exception())
        finally:
            self._ws_clients.remove(ws)
            _LOGGER.info("WebSocket client disconnected (remaining: %d)", len(self._ws_clients))
        
        return ws
    
    # === Mobile App API Handlers ===
    
    async def _handle_mobile_register(self, request: web.Request) -> web.Response:
        """
        Register a mobile device for tracerouting back to home server.
        
        Returns a token that the mobile app uses to submit traceroutes.
        PRIVACY: This is opt-in per user - disabled by default.
        """
        data = await request.json()
        
        # Require a shared secret or HA auth to register
        auth_token = request.headers.get("Authorization", "")
        if not auth_token:
            return web.json_response({"error": "Authorization required"}, status=401)
        
        device_name = data.get("device_name", "Mobile Device")
        
        # Generate a unique token for this mobile device
        mobile_token = secrets.token_urlsafe(32)
        self._mobile_tokens[mobile_token] = {
            "peer_id": f"mobile_{secrets.token_hex(8)}",
            "device_name": device_name,
            "created": time.time(),
            "expires": time.time() + 86400 * 30,  # 30 days
            "home_peer_id": self._peer_id,
        }
        
        return web.json_response({
            "token": mobile_token,
            "home_server": {
                "peer_id": self._peer_id,
                "display_name": self._display_name,
                "host": self._host,
                "port": self._actual_port,
            },
            "expires_in": 86400 * 30,
        })
    
    async def _handle_mobile_traceroute(self, request: web.Request) -> web.Response:
        """
        Receive traceroute from mobile app back to home server.
        
        Mobile app traces route from current location back to HA instance.
        """
        token = request.headers.get("X-Mobile-Token", "")
        
        if token not in self._mobile_tokens:
            return web.json_response({"error": "Invalid token"}, status=401)
        
        token_data = self._mobile_tokens[token]
        
        # Check expiry
        if time.time() > token_data.get("expires", 0):
            del self._mobile_tokens[token]
            return web.json_response({"error": "Token expired"}, status=401)
        
        data = await request.json()
        
        # Create SharedTraceroute from mobile data
        traceroute = SharedTraceroute(
            traceroute_id=secrets.token_hex(8),
            source_peer_id=token_data["peer_id"],
            source_display_name=token_data.get("device_name", "Mobile"),
            target_peer_id=token_data["home_peer_id"],
            target_ip=data.get("target_ip", ""),
            target_display_name=self._display_name,
            timestamp=time.time(),
            hops=data.get("hops", []),
            total_time_ms=data.get("total_time_ms"),
            success=data.get("success", False),
            path_summary=data.get("path_summary"),
            is_mobile=True,
        )
        
        # Store and broadcast (if sharing enabled)
        if self._share_data:
            await self._store_and_broadcast_traceroute(traceroute)
        else:
            # Store locally only
            self._shared_traceroutes[traceroute.traceroute_id] = traceroute
        
        return web.json_response({
            "accepted": True,
            "traceroute_id": traceroute.traceroute_id,
        })
    
    async def _handle_mobile_status(self, request: web.Request) -> web.Response:
        """Get status for mobile app - home server info and recent traceroutes."""
        token = request.headers.get("X-Mobile-Token", "")
        
        if token not in self._mobile_tokens:
            return web.json_response({"error": "Invalid token"}, status=401)
        
        token_data = self._mobile_tokens[token]
        
        # Get recent mobile traceroutes from this device
        mobile_traceroutes = [
            t.to_dict() for t in self._shared_traceroutes.values()
            if t.source_peer_id == token_data["peer_id"]
        ][-10:]  # Last 10
        
        return web.json_response({
            "home_server": {
                "peer_id": self._peer_id,
                "display_name": self._display_name,
                "online": True,
            },
            "recent_traceroutes": mobile_traceroutes,
            "token_expires": token_data.get("expires"),
        })
    
    # === Sharded Storage Handlers ===
    
    async def _handle_shard_store(self, request: web.Request) -> web.Response:
        """Handle request to store sharded data."""
        data = await request.json()
        
        if "data" not in data:
            return web.json_response({"error": "Missing data"}, status=400)
        
        try:
            sharded_data = ShardedData.from_dict(data["data"])
            stored = await self._sharded_storage.store(sharded_data)
            return web.json_response({"accepted": True, "stored_locally": stored})
        except Exception as e:
            _LOGGER.error("Failed to store sharded data: %s", e)
            return web.json_response({"error": str(e)}, status=500)
    
    async def _handle_shard_query(self, request: web.Request) -> web.Response:
        """Handle query for sharded data by geohash."""
        geohash = request.query.get("geohash", "")
        data_type_str = request.query.get("type")
        
        if not geohash:
            return web.json_response({"error": "Missing geohash"}, status=400)
        
        data_type = None
        if data_type_str:
            try:
                data_type = DataType(data_type_str)
            except ValueError:
                pass
        
        items = await self._sharded_storage.get_by_geohash(geohash, data_type)
        
        return web.json_response({
            "items": [item.to_dict() for item in items],
            "geohash": geohash,
            "count": len(items),
        })
    
    async def _handle_shard_region(self, request: web.Request) -> web.Response:
        """
        Load all data for a map region (on-demand loading).
        
        Returns:
        - Traceroutes in the region
        - Infrastructure (permanent)
        - Peers with decay factors
        """
        lat = float(request.query.get("lat", 0))
        lon = float(request.query.get("lon", 0))
        zoom = int(request.query.get("zoom", 10))
        
        # Calculate geohash based on zoom
        if zoom >= 12:
            precision = 5
        elif zoom >= 8:
            precision = 4
        else:
            precision = 3
        
        geohash = encode_geohash(lat, lon, precision)
        
        # Get all data for this region
        traceroutes = await self._sharded_storage.get_by_geohash(geohash, DataType.TRACEROUTE)
        infrastructure = await self._sharded_storage.get_by_geohash(geohash, DataType.INFRASTRUCTURE)
        cell_towers = await self._sharded_storage.get_by_geohash(geohash, DataType.CELL_TOWER)
        peers = await self._sharded_storage.get_by_geohash(geohash, DataType.PEER_LOCATION)
        
        # Get peers with decay
        peers_with_decay = self.get_peers_with_decay()
        
        return web.json_response({
            "geohash": geohash,
            "traceroutes": [t.to_dict() for t in traceroutes],
            "infrastructure": [i.to_dict() for i in infrastructure],
            "cell_towers": [c.to_dict() for c in cell_towers],
            "peers": [
                {**p.to_dict(), "decay": decay}
                for p, decay in peers_with_decay
            ],
        })
    
    # === Data Sync Helpers ===
    
    async def _store_and_broadcast_traceroute(self, traceroute: SharedTraceroute) -> None:
        """Store traceroute locally and broadcast to all peers."""
        # Store locally
        self._shared_traceroutes[traceroute.traceroute_id] = traceroute
        
        # Also store in sharded storage with geolocation
        if traceroute.hops:
            # Get geohash from first hop with geo data
            for hop in traceroute.hops:
                geo = hop.get("geo", {})
                if geo.get("latitude") and geo.get("longitude"):
                    geohash = encode_geohash(
                        geo["latitude"], geo["longitude"], 
                        GEOHASH_PRECISION_REGION
                    )
                    
                    # Classify if this hop is infrastructure
                    infra_class = classify_infrastructure(
                        hop.get("ip", ""),
                        hop.get("asn_info", {}).get("asn"),
                        hop.get("hostname"),
                    )
                    
                    sharded = ShardedData(
                        data_id=f"tr_{traceroute.traceroute_id}_{hop.get('hop_number', 0)}",
                        data_type=DataType.INFRASTRUCTURE if infra_class["is_permanent"] else DataType.TRACEROUTE,
                        geohash=geohash,
                        data=hop,
                        is_permanent=infra_class["is_permanent"],
                        replication_factor=5 if infra_class["is_permanent"] else 3,
                        source_peer_id=self._peer_id,
                    )
                    await self._sharded_storage.store(sharded)
                    break
        
        # Callback
        if self._on_traceroute_received:
            self._on_traceroute_received(traceroute)
        
        # Broadcast to WebSocket clients
        await self._broadcast_to_ws_clients({
            "type": "traceroute",
            "data": traceroute.to_dict(),
        })
        
        # Broadcast to all peers (for live updates)
        await self._broadcast_to_peers(traceroute)
    
    async def _broadcast_to_ws_clients(self, message: dict[str, Any]) -> None:
        """Send message to all connected WebSocket clients."""
        if not self._ws_clients:
            return
        
        dead_clients = []
        for ws in self._ws_clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead_clients.append(ws)
        
        # Clean up dead connections
        for ws in dead_clients:
            self._ws_clients.remove(ws)
    
    async def _broadcast_to_peers(self, traceroute: SharedTraceroute) -> None:
        """Broadcast traceroute to all connected peers."""
        if not self._peers or not self._share_data:
            return
        
        async with aiohttp.ClientSession() as session:
            for peer in list(self._peers.values()):
                if peer.is_stale:
                    continue
                try:
                    url = f"http://{peer.address}/p2p/broadcast"
                    await session.post(
                        url,
                        json={"traceroute": traceroute.to_dict()},
                        timeout=aiohttp.ClientTimeout(total=5),
                    )
                except Exception:
                    pass  # Best effort broadcast
    
    def _cleanup_old_traceroutes(self) -> None:
        """Remove traceroutes older than max age."""
        cutoff = time.time() - self._traceroute_max_age
        self._shared_traceroutes = {
            tid: t for tid, t in self._shared_traceroutes.items()
            if t.timestamp > cutoff
        }
    
    async def request_full_sync(self) -> None:
        """Request full traceroute data from peers."""
        if not self._peers:
            return
        
        proof = self._generate_contribution_proof()
        
        async with aiohttp.ClientSession() as session:
            for peer in list(self._peers.values())[:5]:  # Ask 5 peers max
                if peer.is_stale:
                    continue
                try:
                    url = f"http://{peer.address}/p2p/sync"
                    async with session.get(
                        url,
                        headers={"X-Contribution-Proof": proof},
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            for tr_data in data.get("traceroutes", []):
                                tr = SharedTraceroute.from_dict(tr_data)
                                if tr.traceroute_id not in self._shared_traceroutes:
                                    self._shared_traceroutes[tr.traceroute_id] = tr
                            _LOGGER.info(
                                "Synced %d traceroutes from %s",
                                len(data.get("traceroutes", [])),
                                peer.display_name or peer.peer_id,
                            )
                            break  # Got data from one peer
                except Exception as e:
                    _LOGGER.debug("Failed to sync from %s: %s", peer.address, e)

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
    
    async def _data_sync_loop(self) -> None:
        """Background task for periodic full data sync with peers."""
        # Initial delay to let peer connections establish
        await asyncio.sleep(30)
        
        while self._running:
            try:
                if self._share_data and self._peers:
                    await self.request_full_sync()
                    self._cleanup_old_traceroutes()
                
                # Sync every 5 minutes
                await asyncio.sleep(300)
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error("Data sync error: %s", e)
                await asyncio.sleep(60)  # Retry sooner on error
    
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
        """Set our location and update sharding responsibility."""
        self._my_location = (lat, lon)
        self._my_geohash = encode_geohash(lat, lon, GEOHASH_PRECISION_REGION)
        
        # Update sharded storage with our location
        self._sharded_storage.set_my_location(lat, lon)
        
        _LOGGER.debug("Location set: %.4f, %.4f (geohash: %s)", lat, lon, self._my_geohash)
    
    def set_viewed_region(self, lat: float, lon: float, zoom: int = 10) -> None:
        """
        Set the map region currently being viewed.
        
        This triggers on-demand loading of data for that region.
        """
        # Calculate geohash precision based on zoom level
        if zoom >= 12:
            precision = 5  # ~5km
        elif zoom >= 8:
            precision = 4  # ~39km
        else:
            precision = 3  # ~156km
        
        geohash = encode_geohash(lat, lon, precision)
        
        if geohash not in self._viewed_geohashes:
            self._viewed_geohashes.add(geohash)
            # Trigger async load (fire and forget)
            asyncio.create_task(self._load_region_data(geohash))
    
    async def _load_region_data(self, geohash: str) -> None:
        """Load data for a region from the network."""
        if not self._share_data:
            return
        
        try:
            # Load traceroutes for this region
            data = await self._sharded_storage.get_by_geohash(geohash, DataType.TRACEROUTE)
            _LOGGER.debug("Loaded %d traceroutes for region %s", len(data), geohash)
            
            # Load infrastructure (always load)
            infra = await self._sharded_storage.get_by_geohash(geohash, DataType.INFRASTRUCTURE)
            _LOGGER.debug("Loaded %d infrastructure items for region %s", len(infra), geohash)
            
            # Broadcast to WebSocket clients
            await self._broadcast_to_ws_clients({
                "type": "region_data",
                "geohash": geohash,
                "traceroutes": [d.to_dict() for d in data],
                "infrastructure": [d.to_dict() for d in infra],
            })
        except Exception as e:
            _LOGGER.debug("Failed to load region %s: %s", geohash, e)
    
    def set_sharing_enabled(self, enabled: bool) -> None:
        """Enable or disable data sharing with network."""
        self._share_data = enabled
        _LOGGER.info("Data sharing %s", "enabled" if enabled else "disabled")
    
    @property
    def sharing_enabled(self) -> bool:
        """Check if data sharing is enabled."""
        return self._share_data
    
    def get_peers(self) -> list[P2PPeer]:
        """Get list of known peers with decay factors."""
        visible = []
        for peer in self._peers.values():
            if peer.is_stale:
                # Update decay manager
                pass
            else:
                self._decay_manager.update_node(peer.peer_id)
                visible.append(peer)
        return visible
    
    def get_peers_with_decay(self) -> list[tuple[P2PPeer, float]]:
        """Get peers with their decay factors for visualization."""
        result = []
        visible_nodes = self._decay_manager.get_visible_nodes()
        visible_ids = {pid for pid, _ in visible_nodes}
        
        for peer in self._peers.values():
            if peer.peer_id in visible_ids:
                decay = self._decay_manager.get_decay_factor(peer.peer_id)
                result.append((peer, decay))
        
        return result
    
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
    
    def get_shared_traceroutes(self) -> list[SharedTraceroute]:
        """Get all shared traceroutes from all nodes."""
        self._cleanup_old_traceroutes()
        return list(self._shared_traceroutes.values())
    
    def get_all_hops(self) -> list[dict[str, Any]]:
        """
        Get all hops from all traceroutes for accurate map visualization.
        
        Returns deduplicated hops with their geolocation for mapping.
        """
        seen_ips: dict[str, dict] = {}
        
        for traceroute in self._shared_traceroutes.values():
            for hop in traceroute.hops:
                ip = hop.get("ip") or hop.get("ip_address")
                if ip and ip not in seen_ips:
                    seen_ips[ip] = {
                        "ip": ip,
                        "geo": hop.get("geo"),
                        "asn": hop.get("asn_info"),
                        "infrastructure": hop.get("infrastructure"),
                        "hop_number": hop.get("hop_number"),
                    }
        
        return list(seen_ips.values())
    
    def get_mobile_tokens(self) -> list[dict[str, Any]]:
        """Get list of registered mobile devices."""
        return [
            {
                "device_name": data.get("device_name"),
                "peer_id": data.get("peer_id"),
                "created": data.get("created"),
                "expires": data.get("expires"),
            }
            for data in self._mobile_tokens.values()
            if time.time() < data.get("expires", 0)
        ]
    
    def revoke_mobile_token(self, peer_id: str) -> bool:
        """Revoke a mobile device token."""
        for token, data in list(self._mobile_tokens.items()):
            if data.get("peer_id") == peer_id:
                del self._mobile_tokens[token]
                return True
        return False
    
    async def submit_traceroute(self, target_peer_id: str, traceroute_data: dict) -> None:
        """Submit traceroute results to the network."""
        data = {
            "source_peer_id": self._peer_id,
            "source_display_name": self._display_name,
            "target_peer_id": target_peer_id,
            "traceroute": traceroute_data,
        }
        
        # Add to our topology
        self._add_traceroute_to_topology(data)
        
        # Create SharedTraceroute for live sync
        if self._share_data:
            shared = SharedTraceroute(
                traceroute_id=secrets.token_hex(8),
                source_peer_id=self._peer_id,
                source_display_name=self._display_name,
                target_peer_id=target_peer_id,
                target_ip=traceroute_data.get("target", ""),
                target_display_name=traceroute_data.get("target_name"),
                timestamp=time.time(),
                hops=traceroute_data.get("hops", []),
                total_time_ms=traceroute_data.get("total_time_ms"),
                success=traceroute_data.get("success", False),
                path_summary=traceroute_data.get("path_summary"),
            )
            await self._store_and_broadcast_traceroute(shared)
        
        # Share with peers (legacy method)
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
