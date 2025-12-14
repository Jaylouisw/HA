"""Constants for the HAIMish integration."""

DOMAIN = "ham_network"
NAME = "HAIMish"
VERSION = "2.0.0"

# Configuration keys
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_DISPLAY_NAME = "display_name"
CONF_PUBLIC_URL = "public_url"
CONF_PEER_PORT = "peer_port"
CONF_DISCOVERY_SERVER = "discovery_server"
CONF_ENABLE_GEO_ENRICHMENT = "enable_geo_enrichment"

# Privacy configuration keys
CONF_SHARE_LOCATION = "share_location"
CONF_SHARE_EXACT_LOCATION = "share_exact_location"
CONF_LOCATION_FUZZING_KM = "location_fuzzing_km"
CONF_SHARE_HOSTNAME = "share_hostname"
CONF_SHARE_NETWORK_INFO = "share_network_info"
CONF_ANONYMOUS_MODE = "anonymous_mode"
CONF_LEADERBOARD_VISIBLE = "leaderboard_visible"
CONF_LEADERBOARD_ANONYMOUS = "leaderboard_anonymous"

# Data sharing configuration (PRIVACY: Disabled by default)
CONF_SHARE_TRACEROUTE_DATA = "share_traceroute_data"  # Share traceroutes with network
CONF_ENABLE_MOBILE_TRACKING = "enable_mobile_tracking"  # Allow mobile app to trace back

# Privacy toggle tracking
CONF_LAST_PRIVACY_CHANGE = "last_privacy_change"
CONF_PRIVACY_COOLDOWN_HOURS = 24  # Can only change privacy settings once per day

# Default values
# Port 0 = auto-assign (like BitTorrent) - users can set a specific port if needed
DEFAULT_PEER_PORT = 0  # Auto-assign - dynamic port like BitTorrent
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes
DEFAULT_LOCATION_FUZZING_KM = 10  # Fuzz location by ~10km for privacy
DEFAULT_BOOTSTRAP_PEERS = []  # Initial peers to connect to (can be empty for local-only)
DEFAULT_DISCOVERY_SERVER = ""  # No central server by default (P2P mode)

# P2P Network settings
P2P_PROTOCOL_VERSION = "1.0"
P2P_MAX_PEERS = 50
P2P_PEER_TIMEOUT = 600  # 10 minutes without heartbeat = offline
P2P_GOSSIP_INTERVAL = 60  # Share peer list every minute
P2P_DHT_REPLICATION = 3  # Store data on 3 peers

# Platforms
PLATFORMS = ["sensor"]

# Services
SERVICE_TRACEROUTE = "traceroute"
SERVICE_TRACEROUTE_ALL = "traceroute_all"
SERVICE_REFRESH_PEERS = "refresh_peers"
SERVICE_UPDATE_LOCATION = "update_location"
SERVICE_NETWORK_SCAN = "network_scan"

# Attributes
ATTR_PEERS = "peers"
ATTR_NETWORK_TOPOLOGY = "network_topology"
ATTR_LAST_TRACEROUTE = "last_traceroute"
ATTR_HOP_COUNT = "hop_count"
ATTR_LATENCY = "latency"
ATTR_LEADERBOARD = "leaderboard"
ATTR_MY_STATS = "my_stats"
ATTR_LAYER2_INFO = "layer2_info"
ATTR_LAYER3_INFO = "layer3_info"

# Leaderboard categories
LEADERBOARD_UPTIME = "uptime"
LEADERBOARD_TRACEROUTES = "traceroute_count"
LEADERBOARD_TOTAL_HOPS = "total_hops"
LEADERBOARD_PEERS_DISCOVERED = "peers_discovered"
LEADERBOARD_CONTRIBUTION_SCORE = "contribution_score"

# Events
EVENT_PEER_DISCOVERED = f"{DOMAIN}_peer_discovered"
EVENT_PEER_LOST = f"{DOMAIN}_peer_lost"
EVENT_TRACEROUTE_COMPLETE = f"{DOMAIN}_traceroute_complete"
EVENT_PRIVACY_CHANGED = f"{DOMAIN}_privacy_changed"
EVENT_LEADERBOARD_UPDATE = f"{DOMAIN}_leaderboard_update"
EVENT_NETWORK_SCAN_COMPLETE = f"{DOMAIN}_network_scan_complete"
EVENT_TRACEROUTE_RECEIVED = f"{DOMAIN}_traceroute_received"  # New traceroute from network
EVENT_MOBILE_TRACEROUTE = f"{DOMAIN}_mobile_traceroute"  # Traceroute from mobile app

# Privacy levels
PRIVACY_FULL_SHARE = "full"  # Share everything
PRIVACY_ANONYMOUS = "anonymous"  # Contribute but anonymous
PRIVACY_LOCATION_ONLY = "location_only"  # Only share fuzzed location
PRIVACY_RECEIVE_ONLY = "receive_only"  # Don't contribute (can't see map)
PRIVACY_DISABLED = "disabled"  # Completely off
