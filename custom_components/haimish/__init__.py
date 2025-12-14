"""The HAM Network Map integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import HAMNetworkCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the HAM Network component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HAM Network from a config entry."""
    coordinator = HAMNetworkCoordinator(hass, entry)
    
    # Start auto-discovery and P2P networking
    await coordinator.async_start()
    
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await _async_setup_services(hass, coordinator)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Shutdown coordinator (stops auto-discovery, P2P, saves caches)
        if coordinator:
            await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def _async_setup_services(hass: HomeAssistant, coordinator: HAMNetworkCoordinator) -> None:
    """Set up HAM Network services."""
    from .const import SERVICE_TRACEROUTE, SERVICE_REFRESH_PEERS
    
    async def handle_traceroute(call) -> None:
        """Handle traceroute service call."""
        target_peer = call.data.get("target_peer")
        await coordinator.async_traceroute(target_peer)
    
    async def handle_refresh_peers(call) -> None:
        """Handle refresh peers service call."""
        await coordinator.async_request_refresh()
    
    hass.services.async_register(DOMAIN, SERVICE_TRACEROUTE, handle_traceroute)
    hass.services.async_register(DOMAIN, SERVICE_REFRESH_PEERS, handle_refresh_peers)
