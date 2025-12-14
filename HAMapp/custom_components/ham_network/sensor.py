"""Sensor platform for HAM Network Map."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ATTR_PEERS, ATTR_NETWORK_TOPOLOGY
from .coordinator import HAMNetworkCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAM Network sensors from a config entry."""
    coordinator: HAMNetworkCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        HAMNetworkPeerCountSensor(coordinator, entry),
        HAMNetworkTopologySensor(coordinator, entry),
        HAMNetworkStatusSensor(coordinator, entry),
    ]
    
    async_add_entities(entities)


class HAMNetworkBaseSensor(CoordinatorEntity[HAMNetworkCoordinator], SensorEntity):
    """Base class for HAM Network sensors."""

    def __init__(
        self,
        coordinator: HAMNetworkCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_has_entity_name = True

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "HAM Network Map",
            "manufacturer": "Home Assistant Community",
            "model": "Network Topology",
            "sw_version": "1.0.0",
        }


class HAMNetworkPeerCountSensor(HAMNetworkBaseSensor):
    """Sensor showing the number of connected peers."""

    _attr_name = "Connected Peers"
    _attr_icon = "mdi:home-group"
    _attr_native_unit_of_measurement = "peers"

    def __init__(
        self,
        coordinator: HAMNetworkCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_peer_count"

    @property
    def native_value(self) -> int:
        """Return the number of peers."""
        if self.coordinator.data:
            return self.coordinator.data.get("peer_count", 0)
        return 0

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if not self.coordinator.data:
            return {}
        
        peers = self.coordinator.data.get("peers", [])
        return {
            ATTR_PEERS: peers,
            "online_peers": len([p for p in peers if p.get("online", False)]),
        }


class HAMNetworkTopologySensor(HAMNetworkBaseSensor):
    """Sensor containing the full network topology data."""

    _attr_name = "Network Topology"
    _attr_icon = "mdi:sitemap"

    def __init__(
        self,
        coordinator: HAMNetworkCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_topology"

    @property
    def native_value(self) -> str:
        """Return a summary of the topology."""
        if self.coordinator.data:
            topology = self.coordinator.data.get("topology", {})
            peer_count = len(topology.get("peers", []))
            link_count = len(topology.get("links", []))
            return f"{peer_count} nodes, {link_count} links"
        return "No data"

    @property
    def extra_state_attributes(self):
        """Return the full topology as attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            ATTR_NETWORK_TOPOLOGY: self.coordinator.data.get("topology", {}),
            "my_peer_id": self.coordinator.data.get("my_peer_id"),
            "my_location": self.coordinator.data.get("my_location"),
            "traceroutes": self.coordinator.data.get("traceroutes", {}),
        }


class HAMNetworkStatusSensor(HAMNetworkBaseSensor):
    """Sensor showing the status of this HAM Network instance."""

    _attr_name = "Status"
    _attr_icon = "mdi:check-network"

    def __init__(
        self,
        coordinator: HAMNetworkCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_status"

    @property
    def native_value(self) -> str:
        """Return the status."""
        if self.coordinator.data:
            return "Connected"
        return "Disconnected"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            "peer_id": self.coordinator.data.get("my_peer_id"),
            "location": self.coordinator.data.get("my_location"),
        }
