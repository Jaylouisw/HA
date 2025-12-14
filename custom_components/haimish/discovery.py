"""
Decentralized Auto-Discovery for HAIMish.

Enables Home Assistant instances to find each other automatically
without any central server or pre-configured bootstrap peers.

Discovery Methods (in order of preference):
1. BitTorrent DHT - Uses mainline DHT to find peers by info_hash
2. IPFS PubSub - If IPFS daemon is running, use pubsub for discovery
3. DNS Bootstrap - Fallback DNS TXT records for known community nodes

The key insight: We use existing decentralized infrastructure (BitTorrent DHT)
as a "rendezvous point" where HAIMish nodes can find each other.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import socket
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from pathlib import Path

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Project identifier - all HAIMish nodes use this to find each other
# Note: Keep this ID for backwards compatibility with existing nodes
HAIMISH_NETWORK_ID = "ham-network-homeassistant-community-map-v1"

# DHT settings
DHT_BOOTSTRAP_NODES = [
    ("router.bittorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
    ("router.utorrent.com", 6881),
    ("dht.aelitis.com", 6881),
]

# IPFS settings
IPFS_PUBSUB_TOPIC = "/haimish/discovery/v1"
IPFS_API_DEFAULT = "http://127.0.0.1:5001"

# DNS fallback - community-maintained TXT records
DNS_BOOTSTRAP_DOMAINS = [
    "_haimish-bootstrap.haimish.org",  # Future community domain
]

# Discovery intervals
DISCOVERY_INTERVAL = 300  # 5 minutes
ANNOUNCE_INTERVAL = 600   # 10 minutes


def generate_info_hash(network_id: str = HAIMISH_NETWORK_ID) -> bytes:
    """
    Generate a consistent info_hash for DHT discovery.
    
    All HAIMish nodes use the same info_hash to find each other
    in the BitTorrent DHT network.
    """
    return hashlib.sha1(network_id.encode()).digest()


@dataclass
class DiscoveredPeer:
    """A peer discovered through auto-discovery."""
    
    host: str
    port: int
    discovery_method: str
    discovered_at: datetime = field(default_factory=datetime.now)
    peer_id: str | None = None
    metadata: dict = field(default_factory=dict)
    
    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"


class BitTorrentDHT:
    """
    Minimal BitTorrent DHT client for peer discovery.
    
    Uses the mainline DHT to announce and find HAIMish peers.
    This is a lightweight implementation focused only on peer discovery.
    
    Port Handling:
    - Pass port=0 to auto-assign an available port (recommended)
    - The actual port is available via .port property after start()
    - Announced port can differ from DHT port (for P2P HTTP server)
    """
    
    def __init__(self, port: int = 0):
        """Initialize DHT client. Use port=0 for auto-assignment."""
        self._requested_port = port
        self._actual_port: int = 0
        self._node_id = self._generate_node_id()
        self._socket: socket.socket | None = None
        self._running = False
        self._transaction_id = 0
        self._pending_queries: dict[bytes, asyncio.Future] = {}
        self._known_nodes: list[tuple[str, int]] = list(DHT_BOOTSTRAP_NODES)
        self._peers_found: list[tuple[str, int]] = []
    
    @property
    def port(self) -> int:
        """Get the actual port (after start)."""
        return self._actual_port
    
    def _generate_node_id(self) -> bytes:
        """Generate a random 20-byte node ID."""
        return hashlib.sha1(f"ham-{time.time()}-{random.random()}".encode()).digest()
    
    def _next_transaction_id(self) -> bytes:
        """Generate next transaction ID."""
        self._transaction_id = (self._transaction_id + 1) % 65536
        return struct.pack("!H", self._transaction_id)
    
    async def start(self) -> None:
        """Start the DHT client."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setblocking(False)
        self._socket.bind(("0.0.0.0", self._requested_port))
        
        # Get actual assigned port
        self._actual_port = self._socket.getsockname()[1]
        self._running = True
        
        # Start listener
        asyncio.create_task(self._listen_loop())
        
        # Bootstrap
        await self._bootstrap()
        
        _LOGGER.info("BitTorrent DHT started on port %d", self._actual_port)
    
    async def stop(self) -> None:
        """Stop the DHT client."""
        self._running = False
        if self._socket:
            self._socket.close()
    
    async def _bootstrap(self) -> None:
        """Bootstrap by pinging known nodes."""
        for node in DHT_BOOTSTRAP_NODES:
            try:
                await self._ping(node)
            except Exception as e:
                _LOGGER.debug("Bootstrap ping to %s failed: %s", node, e)
    
    async def _listen_loop(self) -> None:
        """Listen for incoming DHT messages."""
        loop = asyncio.get_event_loop()
        
        while self._running:
            try:
                data, addr = await loop.run_in_executor(
                    None, lambda: self._socket.recvfrom(4096)
                )
                await self._handle_message(data, addr)
            except BlockingIOError:
                await asyncio.sleep(0.1)
            except Exception as e:
                if self._running:
                    _LOGGER.debug("DHT listen error: %s", e)
                await asyncio.sleep(1)
    
    async def _handle_message(self, data: bytes, addr: tuple[str, int]) -> None:
        """Handle incoming DHT message."""
        try:
            msg = self._bencode_decode(data)
            
            if msg.get(b"y") == b"r":
                # Response
                tid = msg.get(b"t")
                if tid in self._pending_queries:
                    self._pending_queries[tid].set_result(msg)
                
                # Extract nodes from response
                response = msg.get(b"r", {})
                if b"nodes" in response:
                    self._parse_nodes(response[b"nodes"])
                if b"values" in response:
                    self._parse_peers(response[b"values"])
                    
        except Exception as e:
            _LOGGER.debug("DHT message parse error: %s", e)
    
    def _parse_nodes(self, nodes_data: bytes) -> None:
        """Parse compact node info."""
        for i in range(0, len(nodes_data), 26):
            if i + 26 <= len(nodes_data):
                node_info = nodes_data[i:i+26]
                # node_id = node_info[:20]
                ip = socket.inet_ntoa(node_info[20:24])
                port = struct.unpack("!H", node_info[24:26])[0]
                if (ip, port) not in self._known_nodes:
                    self._known_nodes.append((ip, port))
    
    def _parse_peers(self, peers_data: list) -> None:
        """Parse compact peer info."""
        for peer_info in peers_data:
            if len(peer_info) >= 6:
                ip = socket.inet_ntoa(peer_info[:4])
                port = struct.unpack("!H", peer_info[4:6])[0]
                if (ip, port) not in self._peers_found:
                    self._peers_found.append((ip, port))
                    _LOGGER.info("DHT found HAM peer: %s:%d", ip, port)
    
    async def _send_query(self, node: tuple[str, int], query: dict) -> dict | None:
        """Send a DHT query and wait for response."""
        tid = self._next_transaction_id()
        query[b"t"] = tid
        
        future = asyncio.Future()
        self._pending_queries[tid] = future
        
        try:
            data = self._bencode_encode(query)
            self._socket.sendto(data, node)
            
            return await asyncio.wait_for(future, timeout=5.0)
        except asyncio.TimeoutError:
            return None
        finally:
            self._pending_queries.pop(tid, None)
    
    async def _ping(self, node: tuple[str, int]) -> bool:
        """Ping a DHT node."""
        query = {
            b"y": b"q",
            b"q": b"ping",
            b"a": {b"id": self._node_id},
        }
        response = await self._send_query(node, query)
        return response is not None
    
    async def get_peers(self, info_hash: bytes) -> list[tuple[str, int]]:
        """
        Find peers for an info_hash in the DHT.
        
        This is how HAIMish nodes find each other - they all query
        for the same info_hash derived from HAIMISH_NETWORK_ID.
        """
        self._peers_found = []
        
        # Query multiple nodes
        nodes_to_query = random.sample(
            self._known_nodes, 
            min(10, len(self._known_nodes))
        )
        
        for node in nodes_to_query:
            query = {
                b"y": b"q",
                b"q": b"get_peers",
                b"a": {
                    b"id": self._node_id,
                    b"info_hash": info_hash,
                },
            }
            await self._send_query(node, query)
        
        # Wait a bit for responses
        await asyncio.sleep(3)
        
        return self._peers_found
    
    async def announce_peer(self, info_hash: bytes, port: int) -> None:
        """
        Announce ourselves as a peer for this info_hash.
        
        This is how we register in the DHT so others can find us.
        """
        nodes_to_announce = random.sample(
            self._known_nodes,
            min(8, len(self._known_nodes))
        )
        
        for node in nodes_to_announce:
            # First get_peers to get a token
            query = {
                b"y": b"q",
                b"q": b"get_peers",
                b"a": {
                    b"id": self._node_id,
                    b"info_hash": info_hash,
                },
            }
            response = await self._send_query(node, query)
            
            if response and b"r" in response:
                token = response[b"r"].get(b"token")
                if token:
                    # Now announce
                    announce_query = {
                        b"y": b"q",
                        b"q": b"announce_peer",
                        b"a": {
                            b"id": self._node_id,
                            b"info_hash": info_hash,
                            b"port": port,
                            b"token": token,
                            b"implied_port": 0,
                        },
                    }
                    await self._send_query(node, announce_query)
    
    # Simple bencode implementation
    def _bencode_encode(self, data: Any) -> bytes:
        """Encode data to bencode format."""
        if isinstance(data, int):
            return f"i{data}e".encode()
        elif isinstance(data, bytes):
            return f"{len(data)}:".encode() + data
        elif isinstance(data, str):
            encoded = data.encode()
            return f"{len(encoded)}:".encode() + encoded
        elif isinstance(data, list):
            return b"l" + b"".join(self._bencode_encode(i) for i in data) + b"e"
        elif isinstance(data, dict):
            items = sorted(data.items(), key=lambda x: x[0])
            return b"d" + b"".join(
                self._bencode_encode(k) + self._bencode_encode(v) 
                for k, v in items
            ) + b"e"
        else:
            raise ValueError(f"Cannot bencode {type(data)}")
    
    def _bencode_decode(self, data: bytes) -> Any:
        """Decode bencode data."""
        return self._bencode_decode_recursive(data, 0)[0]
    
    def _bencode_decode_recursive(self, data: bytes, idx: int) -> tuple[Any, int]:
        """Recursive bencode decoder."""
        if data[idx:idx+1] == b"i":
            end = data.index(b"e", idx)
            return int(data[idx+1:end]), end + 1
        elif data[idx:idx+1] == b"l":
            result = []
            idx += 1
            while data[idx:idx+1] != b"e":
                item, idx = self._bencode_decode_recursive(data, idx)
                result.append(item)
            return result, idx + 1
        elif data[idx:idx+1] == b"d":
            result = {}
            idx += 1
            while data[idx:idx+1] != b"e":
                key, idx = self._bencode_decode_recursive(data, idx)
                value, idx = self._bencode_decode_recursive(data, idx)
                result[key] = value
            return result, idx + 1
        elif data[idx:idx+1].isdigit():
            colon = data.index(b":", idx)
            length = int(data[idx:colon])
            return data[colon+1:colon+1+length], colon + 1 + length
        else:
            raise ValueError(f"Invalid bencode at position {idx}")


class IPFSDiscovery:
    """
    IPFS-based peer discovery using PubSub.
    
    If a user has IPFS running locally, we can use its
    pubsub feature for instant peer discovery.
    """
    
    def __init__(self, api_url: str = IPFS_API_DEFAULT):
        """Initialize IPFS discovery."""
        self._api_url = api_url
        self._available = False
        self._peers_found: list[DiscoveredPeer] = []
        self._subscription_task: asyncio.Task | None = None
    
    async def check_available(self) -> bool:
        """Check if IPFS daemon is available."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._api_url}/api/v0/id",
                    timeout=aiohttp.ClientTimeout(total=2)
                ) as response:
                    if response.status == 200:
                        self._available = True
                        _LOGGER.info("IPFS daemon detected, enabling IPFS discovery")
                        return True
        except Exception:
            pass
        
        self._available = False
        return False
    
    async def start(self, my_port: int, my_peer_id: str) -> None:
        """Start IPFS discovery."""
        if not await self.check_available():
            return
        
        # Start subscription
        self._subscription_task = asyncio.create_task(
            self._subscribe_loop(my_port, my_peer_id)
        )
    
    async def stop(self) -> None:
        """Stop IPFS discovery."""
        if self._subscription_task:
            self._subscription_task.cancel()
    
    async def _subscribe_loop(self, my_port: int, my_peer_id: str) -> None:
        """Subscribe to HAM discovery topic."""
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    # Subscribe to topic
                    url = f"{self._api_url}/api/v0/pubsub/sub"
                    params = {"arg": IPFS_PUBSUB_TOPIC}
                    
                    async with session.post(url, params=params) as response:
                        async for line in response.content:
                            if line:
                                await self._handle_pubsub_message(line)
                                
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.debug("IPFS pubsub error: %s", e)
                await asyncio.sleep(30)
    
    async def _handle_pubsub_message(self, data: bytes) -> None:
        """Handle incoming pubsub message."""
        try:
            import base64
            msg = json.loads(data)
            payload = base64.b64decode(msg.get("data", ""))
            peer_info = json.loads(payload)
            
            if "host" in peer_info and "port" in peer_info:
                peer = DiscoveredPeer(
                    host=peer_info["host"],
                    port=peer_info["port"],
                    discovery_method="ipfs",
                    peer_id=peer_info.get("peer_id"),
                    metadata=peer_info.get("metadata", {}),
                )
                self._peers_found.append(peer)
                _LOGGER.info("IPFS discovered HAM peer: %s", peer.address)
                
        except Exception as e:
            _LOGGER.debug("IPFS message parse error: %s", e)
    
    async def announce(self, host: str, port: int, peer_id: str) -> None:
        """Announce ourselves via IPFS pubsub."""
        if not self._available:
            return
        
        try:
            import base64
            
            message = json.dumps({
                "host": host,
                "port": port,
                "peer_id": peer_id,
                "timestamp": time.time(),
            })
            
            encoded = base64.b64encode(message.encode()).decode()
            
            async with aiohttp.ClientSession() as session:
                url = f"{self._api_url}/api/v0/pubsub/pub"
                params = {"arg": IPFS_PUBSUB_TOPIC}
                data = aiohttp.FormData()
                data.add_field("data", encoded)
                
                await session.post(url, params=params, data=data)
                
        except Exception as e:
            _LOGGER.debug("IPFS announce error: %s", e)
    
    def get_discovered_peers(self) -> list[DiscoveredPeer]:
        """Get peers discovered via IPFS."""
        return list(self._peers_found)


class AutoDiscovery:
    """
    Main auto-discovery coordinator.
    
    Manages multiple discovery methods and provides a unified
    interface for finding HAIMish peers.
    
    Port Handling:
    - p2p_port=0 means auto-assign (recommended for dynamic ports like BitTorrent)
    - DHT uses its own auto-assigned port
    - Call set_p2p_port() after P2P node starts to set actual port
    - Actual ports available via .p2p_port and .dht_port after start()
    """
    
    def __init__(
        self,
        peer_id: str,
        p2p_port: int = 0,  # 0 = auto-assign
        public_host: str | None = None,
        on_peer_discovered: Callable[[DiscoveredPeer], None] | None = None,
    ):
        """Initialize auto-discovery. Use p2p_port=0 for dynamic port."""
        self._peer_id = peer_id
        self._p2p_port = p2p_port  # May be 0 initially, set later
        self._public_host = public_host
        self._on_peer_discovered = on_peer_discovered
        
        # Discovery methods - DHT uses auto-assigned port
        self._dht = BitTorrentDHT(port=0)  # Auto-assign
        self._ipfs = IPFSDiscovery()
        
        # State
        self._running = False
        self._discovered_peers: dict[str, DiscoveredPeer] = {}
        self._tasks: list[asyncio.Task] = []
        
        # Info hash for DHT
        self._info_hash = generate_info_hash()
    
    @property
    def p2p_port(self) -> int:
        """Get the P2P port being announced."""
        return self._p2p_port
    
    @property
    def dht_port(self) -> int:
        """Get the DHT port (available after start)."""
        return self._dht.port
    
    def set_p2p_port(self, port: int) -> None:
        """Set the actual P2P port (call after P2P node starts)."""
        self._p2p_port = port
        _LOGGER.debug("AutoDiscovery P2P port set to %d", port)
    
    async def start(self) -> None:
        """Start auto-discovery."""
        self._running = True
        
        _LOGGER.info("Starting HAIMish auto-discovery...")
        _LOGGER.info("DHT info_hash: %s", self._info_hash.hex())
        
        # Start DHT
        try:
            await self._dht.start()
        except Exception as e:
            _LOGGER.warning("DHT start failed: %s", e)
        
        # Start IPFS if available
        await self._ipfs.start(self._p2p_port, self._peer_id)
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._discovery_loop()),
            asyncio.create_task(self._announce_loop()),
        ]
        
        _LOGGER.info("Auto-discovery started")
    
    async def stop(self) -> None:
        """Stop auto-discovery."""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        await self._dht.stop()
        await self._ipfs.stop()
    
    async def _discovery_loop(self) -> None:
        """Periodically search for peers."""
        while self._running:
            try:
                await self._discover()
                await asyncio.sleep(DISCOVERY_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error("Discovery error: %s", e)
                await asyncio.sleep(60)
    
    async def _announce_loop(self) -> None:
        """Periodically announce ourselves."""
        while self._running:
            try:
                await self._announce()
                await asyncio.sleep(ANNOUNCE_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error("Announce error: %s", e)
                await asyncio.sleep(60)
    
    async def _discover(self) -> None:
        """Run discovery across all methods."""
        _LOGGER.debug("Running peer discovery...")
        
        # DHT discovery
        try:
            dht_peers = await self._dht.get_peers(self._info_hash)
            for host, port in dht_peers:
                await self._add_discovered_peer(host, port, "dht")
        except Exception as e:
            _LOGGER.debug("DHT discovery error: %s", e)
        
        # IPFS discovery
        for peer in self._ipfs.get_discovered_peers():
            await self._add_discovered_peer(
                peer.host, peer.port, "ipfs", peer.peer_id
            )
        
        # DNS bootstrap fallback
        await self._dns_bootstrap()
        
        _LOGGER.info(
            "Discovery complete: %d peers known",
            len(self._discovered_peers)
        )
    
    async def _announce(self) -> None:
        """Announce ourselves via all methods."""
        if not self._public_host:
            # Try to determine public IP
            self._public_host = await self._get_public_ip()
        
        if not self._public_host:
            _LOGGER.debug("No public host, skipping announce")
            return
        
        _LOGGER.debug("Announcing to DHT and IPFS...")
        
        # DHT announce
        try:
            await self._dht.announce_peer(self._info_hash, self._p2p_port)
        except Exception as e:
            _LOGGER.debug("DHT announce error: %s", e)
        
        # IPFS announce
        await self._ipfs.announce(
            self._public_host, 
            self._p2p_port, 
            self._peer_id
        )
    
    async def _add_discovered_peer(
        self, 
        host: str, 
        port: int, 
        method: str,
        peer_id: str | None = None,
    ) -> None:
        """Add a discovered peer."""
        address = f"{host}:{port}"
        
        if address in self._discovered_peers:
            return
        
        # Verify it's actually a HAM peer by pinging
        if await self._verify_ham_peer(host, port):
            peer = DiscoveredPeer(
                host=host,
                port=port,
                discovery_method=method,
                peer_id=peer_id,
            )
            self._discovered_peers[address] = peer
            
            if self._on_peer_discovered:
                self._on_peer_discovered(peer)
            
            _LOGGER.info("Verified HAM peer via %s: %s", method, address)
    
    async def _verify_ham_peer(self, host: str, port: int) -> bool:
        """Verify that a discovered host is actually a HAM peer."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://{host}:{port}/p2p/ping"
                async with session.post(
                    url,
                    json={"peer_id": self._peer_id},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return "peer_id" in data
        except Exception:
            pass
        return False
    
    async def _dns_bootstrap(self) -> None:
        """Try DNS-based bootstrap as fallback."""
        import dns.resolver
        
        for domain in DNS_BOOTSTRAP_DOMAINS:
            try:
                answers = dns.resolver.resolve(domain, "TXT")
                for rdata in answers:
                    txt = str(rdata).strip('"')
                    # Format: "host:port"
                    if ":" in txt:
                        host, port = txt.rsplit(":", 1)
                        await self._add_discovered_peer(
                            host, int(port), "dns"
                        )
            except Exception:
                pass
    
    async def _get_public_ip(self) -> str | None:
        """Get our public IP address."""
        services = [
            "https://api.ipify.org",
            "https://ifconfig.me/ip",
            "https://icanhazip.com",
        ]
        
        async with aiohttp.ClientSession() as session:
            for service in services:
                try:
                    async with session.get(
                        service,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            return (await response.text()).strip()
                except Exception:
                    continue
        return None
    
    def get_discovered_peers(self) -> list[DiscoveredPeer]:
        """Get all discovered peers."""
        return list(self._discovered_peers.values())
    
    def get_bootstrap_addresses(self) -> list[str]:
        """Get discovered peers as bootstrap addresses for P2P."""
        return [p.address for p in self._discovered_peers.values()]
