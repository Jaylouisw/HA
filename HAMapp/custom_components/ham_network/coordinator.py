"""Data update coordinator for HAM Network Map."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any
import uuid

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HAMNetworkAPI, Peer, NetworkTopologyLink
from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_PEER_PORT,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_DISPLAY_NAME,
    CONF_DISCOVERY_SERVER,
    CONF_PUBLIC_URL,
    CONF_SHARE_LOCATION,
    CONF_ENABLE_GEO_ENRICHMENT,
    CONF_PEER_PORT,
    CONF_SHARE_TRACEROUTE_DATA,
    CONF_ENABLE_MOBILE_TRACKING,
    EVENT_TRACEROUTE_COMPLETE,
    EVENT_PEER_DISCOVERED,
    EVENT_TRACEROUTE_RECEIVED,
    EVENT_MOBILE_TRACEROUTE,
)
from .network import NetworkUtilities, TracerouteResult
from .ip_intel import IPIntelligence
from .discovery import AutoDiscovery, DiscoveredPeer
from .p2p import P2PNode, P2PPeer, SharedTraceroute

_LOGGER = logging.getLogger(__name__)


class HAMNetworkCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for HAM Network Map data updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        
        self._entry = entry
        self._peer_id = str(uuid.uuid4())  # Generate unique peer ID
        
        # Initialize API client
        self._api = HAMNetworkAPI(
            discovery_server=entry.data[CONF_DISCOVERY_SERVER],
            peer_id=self._peer_id,
            display_name=entry.data[CONF_DISPLAY_NAME],
            latitude=entry.data[CONF_LATITUDE],
            longitude=entry.data[CONF_LONGITUDE],
            public_url=entry.data.get(CONF_PUBLIC_URL),
        )
        
        # Initialize IP intelligence for geo/ASN enrichment
        self._ip_intel = IPIntelligence(hass.config.path())
        
        # Initialize network utilities with IP intelligence
        self._network = NetworkUtilities(ip_intel=self._ip_intel)
        
        # Geo enrichment preference
        self._enable_geo_enrichment = entry.data.get(CONF_ENABLE_GEO_ENRICHMENT, True)
        
        # P2P port
        self._p2p_port = entry.data.get(CONF_PEER_PORT, DEFAULT_PEER_PORT)
        
        # Privacy settings: Data sharing disabled by default
        self._share_traceroute_data = entry.data.get(CONF_SHARE_TRACEROUTE_DATA, False)
        self._enable_mobile_tracking = entry.data.get(CONF_ENABLE_MOBILE_TRACKING, False)
        
        # Initialize auto-discovery (finds peers via DHT/IPFS without central server)
        self._auto_discovery = AutoDiscovery(
            peer_id=self._peer_id,
            p2p_port=self._p2p_port,
            public_host=entry.data.get(CONF_PUBLIC_URL),
            on_peer_discovered=self._on_auto_discovered_peer,
        )
        
        # Initialize P2P node for direct peer communication
        self._p2p_node: P2PNode | None = None
        
        # Internal state
        self._peers: list[Peer] = []
        self._topology: dict[str, Any] = {"peers": [], "links": []}
        self._traceroute_results: dict[str, TracerouteResult] = {}
        self._shared_traceroutes: list[SharedTraceroute] = []  # From all nodes
        self._share_location = entry.data.get(CONF_SHARE_LOCATION, True)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from discovery server and P2P network."""
        try:
            # Initialize API if needed
            await self._api.async_init()
            
            # Register/send heartbeat
            if self._share_location:
                await self._api.async_register()
            
            # Get peers
            old_peer_ids = {p.peer_id for p in self._peers}
            self._peers = await self._api.async_get_peers()
            
            # Fire event for new peers
            for peer in self._peers:
                if peer.peer_id not in old_peer_ids:
                    self.hass.bus.async_fire(EVENT_PEER_DISCOVERED, {
                        "peer_id": peer.peer_id,
                        "display_name": peer.display_name,
                    })
            
            # Get topology
            self._topology = await self._api.async_get_topology()
            
            # Get shared traceroutes from P2P network
            shared_traceroutes = []
            all_hops = []
            if self._p2p_node:
                self._shared_traceroutes = self._p2p_node.get_shared_traceroutes()
                shared_traceroutes = [t.to_dict() for t in self._shared_traceroutes]
                all_hops = self._p2p_node.get_all_hops()
            
            return {
                "peers": [p.to_dict() for p in self._peers],
                "topology": self._topology,
                "peer_count": len(self._peers),
                "my_peer_id": self._peer_id,
                "my_location": {
                    "latitude": self._entry.data[CONF_LATITUDE],
                    "longitude": self._entry.data[CONF_LONGITUDE],
                    "display_name": self._entry.data[CONF_DISPLAY_NAME],
                },
                "traceroutes": {
                    k: v.to_dict() for k, v in self._traceroute_results.items()
                },
                # New: All traceroutes from all nodes in the network
                "shared_traceroutes": shared_traceroutes,
                "all_hops": all_hops,  # Deduplicated hops for accurate mapping
                "sharing_enabled": self._share_traceroute_data,
                "mobile_tracking_enabled": self._enable_mobile_tracking,
            }
            
        except Exception as err:
            _LOGGER.error("Error updating HAM Network data: %s", err)
            # Return cached data on error
            return {
                "peers": [p.to_dict() for p in self._peers],
                "topology": self._topology,
                "peer_count": len(self._peers),
                "my_peer_id": self._peer_id,
                "my_location": {
                    "latitude": self._entry.data[CONF_LATITUDE],
                    "longitude": self._entry.data[CONF_LONGITUDE],
                    "display_name": self._entry.data[CONF_DISPLAY_NAME],
                },
                "traceroutes": {
                    k: v.to_dict() for k, v in self._traceroute_results.items()
                },
                "shared_traceroutes": [t.to_dict() for t in self._shared_traceroutes],
                "all_hops": [],
                "sharing_enabled": self._share_traceroute_data,
                "mobile_tracking_enabled": self._enable_mobile_tracking,
            }

    async def async_traceroute(self, target_peer_id: str | None = None) -> None:
        """
        Perform traceroute to one or all peers.
        
        If target_peer_id is None, traceroute to all peers.
        Includes geo/ASN enrichment if enabled.
        """
        peers_to_trace = self._peers
        
        if target_peer_id:
            peers_to_trace = [p for p in self._peers if p.peer_id == target_peer_id]
        
        for peer in peers_to_trace:
            if not peer.public_ip:
                _LOGGER.warning("Peer %s has no public IP, skipping traceroute", peer.display_name)
                continue
            
            _LOGGER.info("Running traceroute to %s (%s)", peer.display_name, peer.public_ip)
            
            # Perform traceroute with optional geo enrichment
            result = await self._network.async_traceroute(
                peer.public_ip,
                include_geo=self._enable_geo_enrichment
            )
            self._traceroute_results[peer.peer_id] = result
            
            # Submit results to discovery server
            if result.success:
                await self._api.async_submit_traceroute(peer.peer_id, result.to_dict())
            
            # Fire event with enriched data
            event_data = {
                "target_peer_id": peer.peer_id,
                "target_name": peer.display_name,
                "success": result.success,
                "hop_count": len(result.hops),
                "total_time_ms": result.total_time_ms,
            }
            
            # Include path summary if available
            if result.path_summary:
                event_data["path_summary"] = result.path_summary
            
            self.hass.bus.async_fire(EVENT_TRACEROUTE_COMPLETE, event_data)
        
        # Trigger data refresh
        await self.async_request_refresh()

    async def async_traceroute_all(self) -> None:
        """Perform traceroute to all peers."""
        await self.async_traceroute(None)

    @property
    def peers(self) -> list[Peer]:
        """Return the list of peers."""
        return self._peers

    @property
    def topology(self) -> dict[str, Any]:
        """Return the network topology."""
        return self._topology

    @property
    def peer_id(self) -> str:
        """Return this instance's peer ID."""
        return self._peer_id

    def _on_auto_discovered_peer(self, peer: DiscoveredPeer) -> None:
        """Handle peer discovered via auto-discovery (DHT/IPFS)."""
        _LOGGER.info(
            "Auto-discovered peer via %s: %s",
            peer.discovery_method,
            peer.address
        )
        
        # Fire event
        self.hass.bus.async_fire(EVENT_PEER_DISCOVERED, {
            "peer_id": peer.peer_id or "unknown",
            "address": peer.address,
            "discovery_method": peer.discovery_method,
        })

    def _on_traceroute_received(self, traceroute: SharedTraceroute) -> None:
        """Handle traceroute data received from peers via P2P network.
        
        This is called when another node shares traceroute data with us.
        Updates our local view without storing if we're not responsible.
        """
        _LOGGER.debug(
            "Received shared traceroute from %s to %s (%d hops)",
            traceroute.source_peer_id,
            traceroute.target_peer_id,
            len(traceroute.hops),
        )
        
        # Fire event for any listeners (e.g., Lovelace card updates)
        self.hass.bus.async_fire(EVENT_TRACEROUTE_RECEIVED, {
            "source_peer_id": traceroute.source_peer_id,
            "target_peer_id": traceroute.target_peer_id,
            "hops": traceroute.hops,
            "timestamp": traceroute.timestamp,
            "is_mobile": traceroute.is_mobile,
        })
        
        # If it's a mobile traceroute, fire separate event
        if traceroute.is_mobile:
            self.hass.bus.async_fire(EVENT_MOBILE_TRACEROUTE, {
                "carrier": traceroute.carrier,
                "cell_tower": traceroute.cell_tower_info,
                "hops": traceroute.hops,
            })
    
    async def async_start(self) -> None:
        """Start the coordinator and auto-discovery."""
        _LOGGER.info("Starting HAM Network coordinator...")
        
        # Initialize P2P node FIRST to get actual port
        # Using port=0 for auto-assignment (like BitTorrent)
        self._p2p_node = P2PNode(
            peer_id=self._peer_id,
            host="0.0.0.0",
            port=self._p2p_port,  # 0 = auto-assign
            display_name=self._entry.data[CONF_DISPLAY_NAME],
            on_peer_discovered=lambda p: self.hass.bus.async_fire(
                EVENT_PEER_DISCOVERED, {"peer_id": p.peer_id, "display_name": p.display_name}
            ),
            on_traceroute_received=self._on_traceroute_received,
            share_data=self._share_traceroute_data,  # Privacy: disabled by default
        )
        
        # Set location on P2P node (also sets up sharding responsibility)
        if self._share_location:
            self._p2p_node.set_location(
                self._entry.data[CONF_LATITUDE],
                self._entry.data[CONF_LONGITUDE],
            )
        
        # Start P2P node (this binds the socket and assigns the port)
        await self._p2p_node.start(bootstrap_peers=[])
        
        # Get actual port after P2P starts (may be auto-assigned)
        actual_port = self._p2p_node.port
        _LOGGER.info("P2P node started on port %d", actual_port)
        
        # Set the actual port on auto-discovery so it announces correctly
        self._auto_discovery.set_p2p_port(actual_port)
        
        # Start auto-discovery (DHT + IPFS)
        # This allows finding peers without any central server
        await self._auto_discovery.start()
        
        # After discovery runs, add bootstrap peers
        bootstrap_peers = self._auto_discovery.get_bootstrap_addresses()
        if bootstrap_peers:
            _LOGGER.info(
                "Adding %d bootstrap peers from auto-discovery",
                len(bootstrap_peers)
            )
            # Add discovered peers to the P2P node
            for addr in bootstrap_peers:
                await self._p2p_node.add_bootstrap_peer(addr)
        
        _LOGGER.info(
            "HAM Network started - P2P port: %d, DHT port: %d",
            actual_port,
            self._auto_discovery.dht_port
        )

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        _LOGGER.info("Shutting down HAM Network coordinator...")
        
        # Stop auto-discovery
        await self._auto_discovery.stop()
        
        # Stop P2P node
        if self._p2p_node:
            await self._p2p_node.stop()
        
        await self._api.async_close()
        
        # Save IP intel cache to disk
        if self._ip_intel:
            await self._ip_intel.async_save_cache()
