"""Privacy manager for HAM Network - enforces privacy rules and toggle cooldowns."""
from __future__ import annotations

import hashlib
import logging
import random
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .const import (
    CONF_SHARE_LOCATION,
    CONF_SHARE_EXACT_LOCATION,
    CONF_LOCATION_FUZZING_KM,
    CONF_SHARE_HOSTNAME,
    CONF_SHARE_NETWORK_INFO,
    CONF_ANONYMOUS_MODE,
    CONF_LEADERBOARD_VISIBLE,
    CONF_LEADERBOARD_ANONYMOUS,
    CONF_LAST_PRIVACY_CHANGE,
    CONF_PRIVACY_COOLDOWN_HOURS,
    DEFAULT_LOCATION_FUZZING_KM,
    PRIVACY_FULL_SHARE,
    PRIVACY_ANONYMOUS,
    PRIVACY_LOCATION_ONLY,
    PRIVACY_RECEIVE_ONLY,
    PRIVACY_DISABLED,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class PrivacySettings:
    """Privacy settings for a HAM Network instance."""
    
    # Core sharing settings
    share_location: bool = True
    share_exact_location: bool = False  # If False, location is fuzzed
    location_fuzzing_km: float = DEFAULT_LOCATION_FUZZING_KM
    share_hostname: bool = False
    share_network_info: bool = True  # Share L2/L3 info
    
    # Anonymity
    anonymous_mode: bool = False  # If True, use anonymous ID instead of display name
    
    # Leaderboard
    leaderboard_visible: bool = True  # Appear on leaderboard
    leaderboard_anonymous: bool = False  # Show as anonymous on leaderboard
    
    # Toggle tracking
    last_privacy_change: datetime | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "share_location": self.share_location,
            "share_exact_location": self.share_exact_location,
            "location_fuzzing_km": self.location_fuzzing_km,
            "share_hostname": self.share_hostname,
            "share_network_info": self.share_network_info,
            "anonymous_mode": self.anonymous_mode,
            "leaderboard_visible": self.leaderboard_visible,
            "leaderboard_anonymous": self.leaderboard_anonymous,
            "last_privacy_change": self.last_privacy_change.isoformat() if self.last_privacy_change else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PrivacySettings:
        """Create from dictionary."""
        last_change = None
        if data.get("last_privacy_change"):
            try:
                last_change = datetime.fromisoformat(data["last_privacy_change"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            share_location=data.get("share_location", True),
            share_exact_location=data.get("share_exact_location", False),
            location_fuzzing_km=data.get("location_fuzzing_km", DEFAULT_LOCATION_FUZZING_KM),
            share_hostname=data.get("share_hostname", False),
            share_network_info=data.get("share_network_info", True),
            anonymous_mode=data.get("anonymous_mode", False),
            leaderboard_visible=data.get("leaderboard_visible", True),
            leaderboard_anonymous=data.get("leaderboard_anonymous", False),
            last_privacy_change=last_change,
        )
    
    @property
    def is_contributing(self) -> bool:
        """Check if this instance is contributing data."""
        return self.share_location or self.share_network_info
    
    @property
    def can_view_map(self) -> bool:
        """Check if this instance can view the full map (must contribute)."""
        return self.is_contributing
    
    @property
    def privacy_level(self) -> str:
        """Get the current privacy level."""
        if not self.share_location and not self.share_network_info:
            return PRIVACY_RECEIVE_ONLY
        if self.anonymous_mode:
            return PRIVACY_ANONYMOUS
        if self.share_exact_location and self.share_network_info:
            return PRIVACY_FULL_SHARE
        return PRIVACY_LOCATION_ONLY


class PrivacyManager:
    """Manages privacy settings and enforces rules."""
    
    def __init__(self, peer_id: str, settings: PrivacySettings | None = None):
        """Initialize privacy manager."""
        self._peer_id = peer_id
        self._settings = settings or PrivacySettings()
        self._anonymous_id: str | None = None
    
    @property
    def settings(self) -> PrivacySettings:
        """Get current privacy settings."""
        return self._settings
    
    @property
    def anonymous_id(self) -> str:
        """Get or generate anonymous ID."""
        if self._anonymous_id is None:
            # Create a deterministic but anonymous ID from peer_id
            hash_input = f"ham_anon_{self._peer_id}"
            self._anonymous_id = f"anon_{hashlib.sha256(hash_input.encode()).hexdigest()[:12]}"
        return self._anonymous_id
    
    def can_change_settings(self) -> tuple[bool, str | None]:
        """
        Check if privacy settings can be changed.
        
        Returns (can_change, reason_if_not).
        """
        if self._settings.last_privacy_change is None:
            return True, None
        
        cooldown_end = self._settings.last_privacy_change + timedelta(hours=CONF_PRIVACY_COOLDOWN_HOURS)
        now = datetime.now()
        
        if now < cooldown_end:
            remaining = cooldown_end - now
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            return False, f"Privacy settings can be changed in {hours}h {minutes}m"
        
        return True, None
    
    def update_settings(self, new_settings: dict[str, Any], force: bool = False) -> tuple[bool, str | None]:
        """
        Update privacy settings with cooldown enforcement.
        
        Args:
            new_settings: Dictionary of settings to update
            force: If True, bypass cooldown (for initial setup only)
        
        Returns (success, error_message).
        """
        if not force:
            can_change, reason = self.can_change_settings()
            if not can_change:
                return False, reason
        
        # Update settings
        for key, value in new_settings.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
        
        # Record the change time
        self._settings.last_privacy_change = datetime.now()
        
        _LOGGER.info("Privacy settings updated for peer %s", self._peer_id)
        return True, None
    
    def get_display_name(self, real_name: str) -> str:
        """Get display name based on privacy settings."""
        if self._settings.anonymous_mode:
            return self.anonymous_id
        return real_name
    
    def get_shareable_location(self, lat: float, lon: float) -> tuple[float, float] | None:
        """
        Get location to share based on privacy settings.
        
        Returns (lat, lon) or None if location shouldn't be shared.
        """
        if not self._settings.share_location:
            return None
        
        if self._settings.share_exact_location:
            return lat, lon
        
        # Fuzz the location
        return self._fuzz_location(lat, lon, self._settings.location_fuzzing_km)
    
    def _fuzz_location(self, lat: float, lon: float, km: float) -> tuple[float, float]:
        """
        Add random offset to location for privacy.
        
        Uses a deterministic random based on peer_id so the fuzzed location
        is consistent but not reversible.
        """
        # Use peer_id as seed for consistent fuzzing
        seed = int(hashlib.md5(self._peer_id.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        
        # Random angle and distance
        angle = rng.uniform(0, 2 * math.pi)
        # Use sqrt for uniform distribution in circle
        distance = km * math.sqrt(rng.uniform(0, 1))
        
        # Convert km to degrees (approximate)
        # 1 degree latitude ≈ 111 km
        # 1 degree longitude varies with latitude
        lat_offset = (distance * math.cos(angle)) / 111.0
        lon_offset = (distance * math.sin(angle)) / (111.0 * math.cos(math.radians(lat)))
        
        return lat + lat_offset, lon + lon_offset
    
    def filter_outgoing_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Filter data before sharing based on privacy settings."""
        filtered = {}
        
        # Always include peer_id (may be anonymized elsewhere)
        if "peer_id" in data:
            filtered["peer_id"] = data["peer_id"]
        
        # Display name
        if "display_name" in data:
            filtered["display_name"] = self.get_display_name(data["display_name"])
        
        # Location
        if "latitude" in data and "longitude" in data:
            loc = self.get_shareable_location(data["latitude"], data["longitude"])
            if loc:
                filtered["latitude"], filtered["longitude"] = loc
        
        # Network info
        if self._settings.share_network_info:
            for key in ["layer2_info", "layer3_info", "traceroute_data", "hop_count"]:
                if key in data:
                    filtered[key] = data[key]
        
        # Hostname
        if self._settings.share_hostname and "hostname" in data:
            filtered["hostname"] = data["hostname"]
        
        # Stats for leaderboard (always shared if visible, may be anonymized)
        if self._settings.leaderboard_visible:
            for key in ["uptime", "traceroute_count", "total_hops", "contribution_score"]:
                if key in data:
                    filtered[key] = data[key]
        
        # Timestamps
        for key in ["last_seen", "timestamp"]:
            if key in data:
                filtered[key] = data[key]
        
        return filtered
    
    def filter_incoming_data(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """
        Filter incoming data based on our view permissions.
        
        Returns None if we can't view this data (not contributing).
        """
        if not self._settings.can_view_map:
            # Only return minimal info
            return {
                "peer_count": data.get("peer_count", 0),
                "message": "Enable sharing to view the full map",
            }
        
        return data
    
    def get_leaderboard_entry(self, stats: dict[str, Any], real_name: str) -> dict[str, Any] | None:
        """Get leaderboard entry based on settings."""
        if not self._settings.leaderboard_visible:
            return None
        
        entry = {
            "peer_id": self.anonymous_id if self._settings.leaderboard_anonymous else self._peer_id,
            "display_name": "Anonymous" if self._settings.leaderboard_anonymous else real_name,
            "anonymous": self._settings.leaderboard_anonymous,
            **stats,
        }
        
        return entry
