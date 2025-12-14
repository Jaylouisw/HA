"""Network utilities for HAM Network Map - traceroute and peer communication."""
from __future__ import annotations

import asyncio
import logging
import socket
import struct
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence
    from .ip_intel import IPIntelligence, EnrichedHop

_LOGGER = logging.getLogger(__name__)


@dataclass
class TracerouteHop:
    """Represents a single hop in a traceroute."""
    
    hop_number: int
    ip_address: str | None
    hostname: str | None
    rtt_ms: float | None  # Round-trip time in milliseconds
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "hop": self.hop_number,
            "ip": self.ip_address,
            "hostname": self.hostname,
            "rtt_ms": self.rtt_ms,
        }


@dataclass
class TracerouteResult:
    """Result of a traceroute operation."""
    
    target: str
    target_ip: str | None
    hops: list[TracerouteHop] = field(default_factory=list)
    success: bool = False
    error: str | None = None
    timestamp: float = field(default_factory=time.time)
    total_time_ms: float | None = None
    # Enriched data (geo, ASN, IXP info)
    enriched_hops: list[Any] = field(default_factory=list)  # List of EnrichedHop
    path_summary: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "target": self.target,
            "target_ip": self.target_ip,
            "hops": [hop.to_dict() for hop in self.hops],
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
            "total_time_ms": self.total_time_ms,
            "hop_count": len(self.hops),
        }
        
        # Include enriched data if available
        if self.enriched_hops:
            result["enriched_hops"] = [
                hop.to_dict() if hasattr(hop, 'to_dict') else hop 
                for hop in self.enriched_hops
            ]
        if self.path_summary:
            result["path_summary"] = self.path_summary
            
        return result


class NetworkUtilities:
    """Network utility functions for HAM Network Map."""
    
    def __init__(
        self, 
        timeout: float = 2.0, 
        max_hops: int = 30,
        ip_intel: IPIntelligence | None = None
    ):
        """Initialize network utilities.
        
        Args:
            timeout: Timeout for network operations in seconds
            max_hops: Maximum number of hops for traceroute
            ip_intel: Optional IPIntelligence instance for geo/ASN enrichment
        """
        self._timeout = timeout
        self._max_hops = max_hops
        self._ip_intel = ip_intel
    
    def set_ip_intel(self, ip_intel: IPIntelligence) -> None:
        """Set the IP intelligence instance."""
        self._ip_intel = ip_intel
    
    async def async_traceroute(
        self, 
        target: str, 
        include_geo: bool = False
    ) -> TracerouteResult:
        """
        Perform an async traceroute to the target.
        
        Uses ICMP on Unix-like systems, falls back to UDP on Windows.
        
        Args:
            target: Target hostname or IP address
            include_geo: If True and ip_intel is available, enrich hops with
                        geographic, ASN, and infrastructure data
        
        Returns:
            TracerouteResult with optional enriched hop data
        """
        result = TracerouteResult(target=target, target_ip=None)
        start_time = time.time()
        
        try:
            # Resolve hostname to IP
            target_ip = await self._async_resolve_hostname(target)
            if not target_ip:
                result.error = f"Could not resolve hostname: {target}"
                return result
            
            result.target_ip = target_ip
            
            # Perform traceroute using system command (cross-platform)
            hops = await self._async_system_traceroute(target)
            result.hops = hops
            result.success = len(hops) > 0
            result.total_time_ms = (time.time() - start_time) * 1000
            
            # Enrich with geo/ASN data if requested and available
            if include_geo and self._ip_intel and hops:
                try:
                    enriched = await self._ip_intel.enrich_traceroute(hops)
                    result.enriched_hops = enriched
                    result.path_summary = self._ip_intel.generate_path_summary(enriched)
                    _LOGGER.debug(
                        "Enriched %d hops with geo/ASN data for %s",
                        len(enriched), target
                    )
                except Exception as enrich_err:
                    _LOGGER.warning(
                        "Failed to enrich traceroute data: %s", enrich_err
                    )
            
        except Exception as e:
            _LOGGER.error("Traceroute failed: %s", str(e))
            result.error = str(e)
        
        return result
    
    async def _async_resolve_hostname(self, hostname: str) -> str | None:
        """Resolve hostname to IP address asynchronously."""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.getaddrinfo(
                hostname, None, family=socket.AF_INET, type=socket.SOCK_STREAM
            )
            if result:
                return result[0][4][0]
        except socket.gaierror as e:
            _LOGGER.warning("Failed to resolve %s: %s", hostname, e)
        return None
    
    async def _async_system_traceroute(self, target: str) -> list[TracerouteHop]:
        """
        Perform traceroute using system command.
        
        Cross-platform: uses 'traceroute' on Unix, 'tracert' on Windows.
        """
        import platform
        import re
        
        system = platform.system().lower()
        
        if system == "windows":
            cmd = ["tracert", "-d", "-h", str(self._max_hops), "-w", str(int(self._timeout * 1000)), target]
        else:
            cmd = ["traceroute", "-n", "-m", str(self._max_hops), "-w", str(self._timeout), target]
        
        hops: list[TracerouteHop] = []
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._timeout * self._max_hops + 10
            )
            
            output = stdout.decode("utf-8", errors="ignore")
            
            # Parse the output
            hops = self._parse_traceroute_output(output, system)
            
        except asyncio.TimeoutError:
            _LOGGER.warning("Traceroute to %s timed out", target)
        except FileNotFoundError:
            _LOGGER.error("Traceroute command not found on this system")
        except Exception as e:
            _LOGGER.error("Error running traceroute: %s", e)
        
        return hops
    
    def _parse_traceroute_output(self, output: str, system: str) -> list[TracerouteHop]:
        """Parse traceroute output into structured hops."""
        import re
        
        hops: list[TracerouteHop] = []
        lines = output.strip().split("\n")
        
        # Different regex patterns for Windows vs Unix
        if system == "windows":
            # Windows tracert format: "  1    <1 ms    <1 ms    <1 ms  192.168.1.1"
            pattern = r"^\s*(\d+)\s+(?:(\d+)\s*ms|[<*]\d*\s*ms|\*)\s+(?:(\d+)\s*ms|[<*]\d*\s*ms|\*)\s+(?:(\d+)\s*ms|[<*]\d*\s*ms|\*)\s+(\S+)"
        else:
            # Unix traceroute format: " 1  192.168.1.1  0.425 ms  0.359 ms  0.318 ms"
            pattern = r"^\s*(\d+)\s+(\S+)\s+(\d+\.?\d*)\s*ms"
        
        for line in lines:
            match = re.search(pattern, line)
            if match:
                if system == "windows":
                    hop_num = int(match.group(1))
                    ip_addr = match.group(5) if match.group(5) != "*" else None
                    # Get first valid RTT
                    rtt = None
                    for g in [2, 3, 4]:
                        if match.group(g):
                            rtt = float(match.group(g))
                            break
                else:
                    hop_num = int(match.group(1))
                    ip_addr = match.group(2) if match.group(2) != "*" else None
                    rtt = float(match.group(3)) if match.group(3) else None
                
                hops.append(TracerouteHop(
                    hop_number=hop_num,
                    ip_address=ip_addr,
                    hostname=None,  # Could do reverse DNS lookup
                    rtt_ms=rtt,
                ))
            elif "*" in line and re.match(r"^\s*(\d+)", line):
                # Handle timeout hops
                hop_match = re.match(r"^\s*(\d+)", line)
                if hop_match:
                    hops.append(TracerouteHop(
                        hop_number=int(hop_match.group(1)),
                        ip_address=None,
                        hostname=None,
                        rtt_ms=None,
                    ))
        
        return hops
    
    async def async_ping(self, target: str, count: int = 3) -> dict:
        """
        Perform async ping to target.
        
        Returns dict with success status, average RTT, and packet loss.
        """
        import platform
        
        system = platform.system().lower()
        
        if system == "windows":
            cmd = ["ping", "-n", str(count), "-w", str(int(self._timeout * 1000)), target]
        else:
            cmd = ["ping", "-c", str(count), "-W", str(int(self._timeout)), target]
        
        result = {
            "target": target,
            "success": False,
            "avg_rtt_ms": None,
            "packet_loss": 100.0,
        }
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=self._timeout * count + 5
            )
            
            output = stdout.decode("utf-8", errors="ignore")
            
            # Parse ping results
            import re
            
            # Look for average RTT
            if system == "windows":
                avg_match = re.search(r"Average\s*=\s*(\d+)ms", output)
                loss_match = re.search(r"\((\d+)%\s*loss\)", output)
            else:
                avg_match = re.search(r"avg.*?=\s*[\d.]+/([\d.]+)/", output)
                loss_match = re.search(r"(\d+)%\s*packet loss", output)
            
            if avg_match:
                result["avg_rtt_ms"] = float(avg_match.group(1))
                result["success"] = True
            
            if loss_match:
                result["packet_loss"] = float(loss_match.group(1))
            
        except Exception as e:
            _LOGGER.error("Ping failed: %s", e)
        
        return result


async def get_public_ip() -> str | None:
    """Get the public IP address of this instance."""
    import aiohttp
    
    services = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com",
    ]
    
    async with aiohttp.ClientSession() as session:
        for service in services:
            try:
                async with session.get(service, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        ip = (await response.text()).strip()
                        return ip
            except Exception as e:
                _LOGGER.debug("Failed to get IP from %s: %s", service, e)
                continue
    
    return None
