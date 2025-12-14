/**
 * HAIMish Map - Lovelace Card
 * 
 * A custom Lovelace card that displays Home Assistant community deployments
 * on a geographical map with network topology visualization.
 * 
 * Features:
 * - Geographic map of community HA deployments
 * - Network path visualization with traceroute
 * - ASN transitions and provider network identification
 * - IXP (Internet Exchange Point) detection
 * - Datacenter/cloud provider identification
 * - LIVE real-time updates via Home Assistant events
 */

const CARD_VERSION = '2.1.0';

// Leaflet CSS and JS URLs
const LEAFLET_CSS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
const LEAFLET_JS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';

// Provider colors for ASN visualization
const PROVIDER_COLORS = {
  cloud: '#4285F4',     // Blue for cloud providers
  cdn: '#FF6B35',       // Orange for CDN
  transit: '#9C27B0',   // Purple for transit
  isp: '#4CAF50',       // Green for ISPs
  ixp: '#E91E63',       // Pink for IXPs
  datacenter: '#00BCD4', // Cyan for datacenters
  unknown: '#9E9E9E',   // Grey for unknown
};

// Animation colors
const ANIMATION_COLORS = {
  newPeer: '#4CAF50',
  newTraceroute: '#FF9800',
  pulse: '#03A9F4',
};

// Load external resources
const loadCSS = (url) => {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`link[href="${url}"]`)) {
      resolve();
      return;
    }
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = url;
    link.onload = resolve;
    link.onerror = reject;
    document.head.appendChild(link);
  });
};

const loadScript = (url) => {
  return new Promise((resolve, reject) => {
    if (window.L) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = url;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
};

class HAIMishMapCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._initialized = false;
    this._map = null;
    this._markers = [];
    this._polylines = [];
    this._eventSubscriptions = [];
    this._liveActivityQueue = [];
    this._animatingPaths = new Map();
  }

  static get properties() {
    return {
      hass: {},
      config: {},
    };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error('Please define an entity');
    }
    this.config = {
      title: 'HAIMish',
      height: '400px',
      zoom: 4,
      show_topology: true,
      show_traceroute: true,
      show_path_details: true,      // Show ASN/IXP info on paths
      show_enriched_hops: true,     // Show intermediate hops on map
      color_by_provider: true,      // Color paths by provider type
      show_live_activity: true,     // Show live activity feed
      animate_new_data: true,       // Animate new peers/traceroutes
      marker_color: '#03a9f4',
      my_marker_color: '#4caf50',
      link_color: '#ff9800',
      hop_marker_color: '#9c27b0',
      ixp_marker_color: '#e91e63',
      ...config,
    };
    this._enrichedHopMarkers = [];
  }

  set hass(hass) {
    const oldHass = this._hass;
    this._hass = hass;
    
    if (!this._initialized) {
      this._initialize();
    } else {
      this._updateMap();
    }
    
    // Subscribe to events if hass changed and we have connection
    if (hass && hass.connection && (!oldHass || oldHass.connection !== hass.connection)) {
      this._subscribeToEvents();
    }
  }

  disconnectedCallback() {
    // Clean up event subscriptions
    this._unsubscribeFromEvents();
  }

  async _initialize() {
    try {
      // Load Leaflet
      await loadCSS(LEAFLET_CSS);
      await loadScript(LEAFLET_JS);

      this._render();
      this._initMap();
      this._initialized = true;
      this._updateMap();
      this._subscribeToEvents();
    } catch (error) {
      console.error('Failed to initialize HAIMish Map:', error);
      this._renderError(error);
    }
  }

  _subscribeToEvents() {
    if (!this._hass?.connection) return;
    
    // Unsubscribe from old subscriptions first
    this._unsubscribeFromEvents();
    
    // Subscribe to peer discovered events
    this._hass.connection.subscribeEvents((event) => {
      this._onPeerDiscovered(event.data);
    }, 'haimish_peer_discovered').then(unsub => {
      this._eventSubscriptions.push(unsub);
    }).catch(err => console.debug('Event subscription error:', err));
    
    // Subscribe to traceroute received events
    this._hass.connection.subscribeEvents((event) => {
      this._onTracerouteReceived(event.data);
    }, 'haimish_traceroute_received').then(unsub => {
      this._eventSubscriptions.push(unsub);
    }).catch(err => console.debug('Event subscription error:', err));
    
    // Subscribe to traceroute complete events
    this._hass.connection.subscribeEvents((event) => {
      this._onTracerouteComplete(event.data);
    }, 'haimish_traceroute_complete').then(unsub => {
      this._eventSubscriptions.push(unsub);
    }).catch(err => console.debug('Event subscription error:', err));
    
    // Subscribe to mobile traceroute events
    this._hass.connection.subscribeEvents((event) => {
      this._onMobileTraceroute(event.data);
    }, 'haimish_mobile_traceroute').then(unsub => {
      this._eventSubscriptions.push(unsub);
    }).catch(err => console.debug('Event subscription error:', err));
    
    console.info('HAIMish: Subscribed to live events');
  }

  _unsubscribeFromEvents() {
    this._eventSubscriptions.forEach(unsub => {
      if (typeof unsub === 'function') unsub();
    });
    this._eventSubscriptions = [];
  }

  _onPeerDiscovered(data) {
    console.info('HAIMish: New peer discovered:', data);
    this._addLiveActivity('peer', `New peer: ${data.display_name || data.peer_id}`);
    
    // Animate if we have location
    if (this.config.animate_new_data) {
      this._updateMap();
      // Flash effect on map
      this._flashNotification('🟢 New peer discovered!');
    }
  }

  _onTracerouteReceived(data) {
    console.info('HAIMish: Traceroute received from network:', data);
    this._addLiveActivity('traceroute', `Traceroute: ${data.source_peer_id?.slice(0,8)} → ${data.target_peer_id?.slice(0,8)}`);
    
    if (this.config.animate_new_data && data.hops) {
      this._animateTraceroute(data.hops);
    }
    
    // Refresh to show new data
    this._updateMap();
  }

  _onTracerouteComplete(data) {
    console.info('HAIMish: Traceroute complete:', data);
    const msg = data.success 
      ? `Traceroute to ${data.target_name}: ${data.hop_count} hops, ${data.total_time_ms?.toFixed(0)}ms`
      : `Traceroute to ${data.target_name} failed`;
    this._addLiveActivity('traceroute', msg);
    this._flashNotification(data.success ? '✅ Traceroute complete' : '❌ Traceroute failed');
    this._updateMap();
  }

  _onMobileTraceroute(data) {
    console.info('HAIMish: Mobile traceroute:', data);
    this._addLiveActivity('mobile', `📱 Mobile trace via ${data.carrier || 'unknown carrier'}`);
    this._flashNotification('📱 Mobile traceroute received!');
    this._updateMap();
  }

  _addLiveActivity(type, message) {
    if (!this.config.show_live_activity) return;
    
    const timestamp = new Date().toLocaleTimeString();
    this._liveActivityQueue.unshift({ type, message, timestamp });
    
    // Keep only last 5 activities
    if (this._liveActivityQueue.length > 5) {
      this._liveActivityQueue.pop();
    }
    
    this._updateLiveActivityPanel();
  }

  _updateLiveActivityPanel() {
    const panel = this.shadowRoot.getElementById('live-activity');
    if (!panel) return;
    
    if (this._liveActivityQueue.length === 0) {
      panel.innerHTML = '<div class="activity-empty">Waiting for activity...</div>';
      return;
    }
    
    panel.innerHTML = this._liveActivityQueue.map(item => {
      const icon = item.type === 'peer' ? '👤' : item.type === 'mobile' ? '📱' : '🌐';
      return `
        <div class="activity-item ${item.type}">
          <span class="activity-icon">${icon}</span>
          <span class="activity-message">${item.message}</span>
          <span class="activity-time">${item.timestamp}</span>
        </div>
      `;
    }).join('');
  }

  _flashNotification(message) {
    const notification = this.shadowRoot.getElementById('notification');
    if (!notification) return;
    
    notification.textContent = message;
    notification.classList.add('show');
    
    setTimeout(() => {
      notification.classList.remove('show');
    }, 3000);
  }

  _animateTraceroute(hops) {
    if (!this._map || !hops || hops.length === 0) return;
    
    // Filter hops with valid geo data
    const geoHops = hops.filter(h => h.geo?.latitude && h.geo?.longitude);
    if (geoHops.length < 2) return;
    
    // Create animated path
    const coords = geoHops.map(h => [h.geo.latitude, h.geo.longitude]);
    
    // Create a pulsing polyline
    const animatedPath = L.polyline(coords, {
      color: ANIMATION_COLORS.newTraceroute,
      weight: 4,
      opacity: 0.9,
      className: 'animated-path',
    }).addTo(this._map);
    
    // Add pulse animation to each hop
    geoHops.forEach((hop, index) => {
      setTimeout(() => {
        const pulseMarker = L.circleMarker([hop.geo.latitude, hop.geo.longitude], {
          radius: 8,
          fillColor: ANIMATION_COLORS.pulse,
          color: '#fff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.8,
          className: 'pulse-marker',
        }).addTo(this._map);
        
        // Remove pulse after animation
        setTimeout(() => pulseMarker.remove(), 2000);
      }, index * 200); // Stagger animations
    });
    
    // Remove animated path after a few seconds
    setTimeout(() => animatedPath.remove(), 5000);
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }
        ha-card {
          overflow: hidden;
        }
        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          font-size: 1.2em;
          font-weight: 500;
        }
        .peer-count {
          font-size: 0.8em;
          color: var(--secondary-text-color);
          background: var(--primary-color);
          color: white;
          padding: 2px 8px;
          border-radius: 12px;
        }
        #map-container {
          height: ${this.config.height};
          width: 100%;
          z-index: 0;
        }
        .info-panel {
          padding: 12px 16px;
          border-top: 1px solid var(--divider-color);
          font-size: 0.9em;
        }
        .info-row {
          display: flex;
          justify-content: space-between;
          margin: 4px 0;
        }
        .info-label {
          color: var(--secondary-text-color);
        }
        .path-summary {
          padding: 8px 16px;
          border-top: 1px solid var(--divider-color);
          font-size: 0.85em;
        }
        .path-summary h5 {
          margin: 0 0 8px 0;
          font-size: 0.95em;
        }
        .asn-badge {
          display: inline-block;
          padding: 2px 6px;
          border-radius: 10px;
          font-size: 11px;
          margin: 2px;
          color: white;
        }
        .asn-transit {
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          gap: 4px;
          margin: 4px 0;
        }
        .asn-arrow {
          color: var(--secondary-text-color);
        }
        .ixp-indicator {
          background: #E91E63;
          color: white;
          padding: 2px 8px;
          border-radius: 8px;
          font-size: 10px;
          margin: 2px;
        }
        .path-stats {
          display: flex;
          gap: 16px;
          margin-top: 8px;
          flex-wrap: wrap;
        }
        .path-stat {
          text-align: center;
        }
        .path-stat-value {
          font-size: 1.2em;
          font-weight: bold;
          color: var(--primary-color);
        }
        .path-stat-label {
          font-size: 0.75em;
          color: var(--secondary-text-color);
        }
        .actions {
          padding: 8px 16px;
          display: flex;
          gap: 8px;
          border-top: 1px solid var(--divider-color);
        }
        .action-btn {
          flex: 1;
          padding: 8px;
          border: none;
          border-radius: 4px;
          background: var(--primary-color);
          color: white;
          cursor: pointer;
          font-size: 0.85em;
        }
        .action-btn:hover {
          opacity: 0.9;
        }
        .legend {
          position: absolute;
          bottom: 20px;
          right: 10px;
          background: white;
          padding: 8px 12px;
          border-radius: 4px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.2);
          z-index: 1000;
          font-size: 12px;
        }
        .legend-item {
          display: flex;
          align-items: center;
          gap: 6px;
          margin: 4px 0;
        }
        .legend-marker {
          width: 12px;
          height: 12px;
          border-radius: 50%;
        }
        .legend-line {
          width: 20px;
          height: 3px;
        }

        /* Leaflet overrides for shadow DOM */
        .leaflet-container {
          font-family: inherit;
        }
        .leaflet-popup-content-wrapper {
          border-radius: 8px;
        }
        .popup-content h4 {
          margin: 0 0 8px 0;
          color: #333;
        }
        .popup-content p {
          margin: 4px 0;
          font-size: 12px;
          color: #666;
        }
        .popup-content .status {
          display: inline-block;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 11px;
        }
        .popup-content .status.online {
          background: #4caf50;
          color: white;
        }
        .popup-content .status.offline {
          background: #9e9e9e;
          color: white;
        }
        
        /* Live activity styles */
        .live-activity {
          max-height: 120px;
          overflow-y: auto;
          padding: 8px 16px;
          border-top: 1px solid var(--divider-color);
          font-size: 0.8em;
          background: var(--card-background-color, #fafafa);
        }
        .live-activity-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        .live-activity-title {
          font-weight: 500;
          color: var(--primary-text-color);
        }
        .live-indicator {
          width: 8px;
          height: 8px;
          background: #4CAF50;
          border-radius: 50%;
          animation: pulse-live 2s infinite;
        }
        @keyframes pulse-live {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.2); }
        }
        .activity-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 4px 0;
          border-bottom: 1px solid var(--divider-color, #eee);
        }
        .activity-item:last-child {
          border-bottom: none;
        }
        .activity-icon {
          font-size: 14px;
        }
        .activity-message {
          flex: 1;
          color: var(--primary-text-color);
        }
        .activity-time {
          color: var(--secondary-text-color);
          font-size: 0.85em;
        }
        .activity-empty {
          color: var(--secondary-text-color);
          font-style: italic;
        }
        
        /* Notification toast */
        .notification {
          position: absolute;
          top: 60px;
          left: 50%;
          transform: translateX(-50%) translateY(-20px);
          background: var(--primary-color, #03a9f4);
          color: white;
          padding: 8px 16px;
          border-radius: 20px;
          font-size: 0.85em;
          opacity: 0;
          transition: opacity 0.3s, transform 0.3s;
          z-index: 1001;
          pointer-events: none;
        }
        .notification.show {
          opacity: 1;
          transform: translateX(-50%) translateY(0);
        }
        
        /* Animated path styles */
        .animated-path {
          animation: dash-animation 1s linear infinite;
        }
        @keyframes dash-animation {
          to { stroke-dashoffset: -20; }
        }
        .pulse-marker {
          animation: pulse-marker 1s ease-out;
        }
        @keyframes pulse-marker {
          0% { transform: scale(1); opacity: 1; }
          100% { transform: scale(2); opacity: 0; }
        }
        
        /* Sharing status indicator */
        .sharing-status {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 4px 8px;
          font-size: 0.75em;
          border-radius: 12px;
        }
        .sharing-status.enabled {
          background: rgba(76, 175, 80, 0.1);
          color: #4CAF50;
        }
        .sharing-status.disabled {
          background: rgba(158, 158, 158, 0.1);
          color: #9E9E9E;
        }
      </style>
      <ha-card>
        <div class="card-header">
          <span>${this.config.title}</span>
          <div style="display: flex; align-items: center; gap: 12px;">
            <span class="sharing-status" id="sharing-status"></span>
            <span class="peer-count" id="peer-count">0 peers</span>
          </div>
        </div>
        <div style="position: relative;">
          <div id="map-container"></div>
          <div class="notification" id="notification"></div>
        </div>
        <div class="info-panel" id="info-panel">
          <div class="info-row">
            <span class="info-label">Status:</span>
            <span id="status">Initializing...</span>
          </div>
          <div class="info-row">
            <span class="info-label">Network Links:</span>
            <span id="link-count">0</span>
          </div>
        </div>
        <div class="path-summary" id="path-summary-panel" style="display: none;">
          <h5>🌐 Path Analysis</h5>
          <div id="asn-path" class="asn-transit"></div>
          <div class="path-stats" id="path-stats"></div>
        </div>
        <div class="live-activity" id="live-activity-container">
          <div class="live-activity-header">
            <span class="live-activity-title">📡 Live Activity</span>
            <div class="live-indicator"></div>
          </div>
          <div id="live-activity">
            <div class="activity-empty">Waiting for activity...</div>
          </div>
        </div>
        <div class="actions">
          <button class="action-btn" id="btn-refresh">
            🔄 Refresh
          </button>
          <button class="action-btn" id="btn-traceroute">
            🌐 Run Traceroute
          </button>
        </div>
      </ha-card>
    `;

    // Set up action buttons
    this.shadowRoot.getElementById('btn-refresh').addEventListener('click', () => {
      this._callService('refresh_peers');
    });
    this.shadowRoot.getElementById('btn-traceroute').addEventListener('click', () => {
      this._callService('traceroute');
    });
  }

  _initMap() {
    const container = this.shadowRoot.getElementById('map-container');
    
    // Get initial center from config or default to center of map
    const defaultLat = this.config.default_latitude || 40;
    const defaultLng = this.config.default_longitude || -95;
    
    this._map = L.map(container, {
      center: [defaultLat, defaultLng],
      zoom: this.config.zoom,
      zoomControl: true,
    });

    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(this._map);

    // Add legend
    this._addLegend();

    // Fix map size issues in shadow DOM
    setTimeout(() => {
      this._map.invalidateSize();
    }, 100);
  }

  _addLegend() {
    const legend = L.control({ position: 'bottomright' });
    legend.onAdd = () => {
      const div = L.DomUtil.create('div', 'legend');
      div.innerHTML = `
        <div class="legend-item">
          <div class="legend-marker" style="background: ${this.config.my_marker_color}"></div>
          <span>My Instance</span>
        </div>
        <div class="legend-item">
          <div class="legend-marker" style="background: ${this.config.marker_color}"></div>
          <span>Community Peer</span>
        </div>
        <div class="legend-item">
          <div class="legend-marker" style="background: ${this.config.hop_marker_color}"></div>
          <span>Network Hop</span>
        </div>
        <div class="legend-item">
          <div class="legend-marker" style="background: ${this.config.ixp_marker_color}"></div>
          <span>IXP/Exchange</span>
        </div>
        <div class="legend-item">
          <div class="legend-line" style="background: ${this.config.link_color}"></div>
          <span>Network Path</span>
        </div>
      `;
      return div;
    };
    legend.addTo(this._map);
  }

  _updateMap() {
    if (!this._map || !this._hass) return;

    const entityId = this.config.entity;
    const state = this._hass.states[entityId];

    if (!state) {
      this._updateStatus('Entity not found');
      return;
    }

    const attrs = state.attributes || {};
    const topology = attrs.network_topology || {};
    const peers = topology.peers || [];
    const links = topology.links || [];
    const myLocation = attrs.my_location || {};
    const myPeerId = attrs.my_peer_id;
    const traceroutes = attrs.traceroutes || {};
    const sharedTraceroutes = attrs.shared_traceroutes || [];
    const sharingEnabled = attrs.sharing_enabled || false;
    const mobileEnabled = attrs.mobile_tracking_enabled || false;

    // Update info panel
    this._updateStatus('Connected');
    this.shadowRoot.getElementById('peer-count').textContent = `${peers.length} peers`;
    this.shadowRoot.getElementById('link-count').textContent = links.length.toString();
    
    // Update sharing status
    const sharingStatus = this.shadowRoot.getElementById('sharing-status');
    if (sharingStatus) {
      if (sharingEnabled) {
        sharingStatus.className = 'sharing-status enabled';
        sharingStatus.innerHTML = '🔗 Sharing';
      } else {
        sharingStatus.className = 'sharing-status disabled';
        sharingStatus.innerHTML = '🔒 Private';
      }
    }

    // Clear existing markers and lines
    this._clearMapLayers();

    // Add my location marker
    if (myLocation.latitude && myLocation.longitude) {
      this._addMarker(
        myLocation.latitude,
        myLocation.longitude,
        myLocation.display_name || 'My Home',
        true,
        { online: true, peer_id: myPeerId }
      );
    }

    // Add peer markers
    peers.forEach(peer => {
      if (peer.latitude && peer.longitude) {
        this._addMarker(
          peer.latitude,
          peer.longitude,
          peer.display_name,
          false,
          peer
        );
      }
    });

    // Add topology links
    if (this.config.show_topology) {
      this._drawTopologyLinks(links, peers, myLocation, myPeerId);
    }

    // Draw enriched traceroute paths if available
    if (this.config.show_enriched_hops) {
      this._drawEnrichedPaths(traceroutes);
      // Also draw shared traceroutes from other nodes
      this._drawSharedTraceroutes(sharedTraceroutes);
    }

    // Update path summary panel if we have traceroute data
    this._updatePathSummary(traceroutes);

    // Fit bounds to show all markers
    if (this._markers.length > 0) {
      const group = L.featureGroup(this._markers);
      this._map.fitBounds(group.getBounds().pad(0.1));
    }
  }

  _drawSharedTraceroutes(sharedTraceroutes) {
    if (!sharedTraceroutes || sharedTraceroutes.length === 0) return;
    
    sharedTraceroutes.forEach(trace => {
      const hops = trace.hops || [];
      const geoHops = hops.filter(h => h.geo?.latitude && h.geo?.longitude);
      
      if (geoHops.length < 2) return;
      
      const coords = geoHops.map(h => [h.geo.latitude, h.geo.longitude]);
      
      // Draw with slightly different style for shared traceroutes
      const polyline = L.polyline(coords, {
        color: trace.is_mobile ? '#9C27B0' : '#607D8B',
        weight: 2,
        opacity: 0.5,
        dashArray: '3, 6',
      }).addTo(this._map);
      
      polyline.bindPopup(`
        <div class="popup-content">
          <h4>${trace.is_mobile ? '📱' : '🌐'} Shared Traceroute</h4>
          <p>From: ${trace.source_peer_id?.slice(0, 8)}...</p>
          <p>To: ${trace.target_peer_id?.slice(0, 8)}...</p>
          <p>Hops: ${hops.length}</p>
          ${trace.carrier ? `<p>Carrier: ${trace.carrier}</p>` : ''}
        </div>
      `);
      
      this._polylines.push(polyline);
    });
  }

  _drawEnrichedPaths(traceroutes) {
    // Clear existing enriched hop markers
    if (this._enrichedHopMarkers) {
      this._enrichedHopMarkers.forEach(m => m.remove());
    }
    this._enrichedHopMarkers = [];

    Object.entries(traceroutes).forEach(([peerId, trace]) => {
      const enrichedHops = trace.enriched_hops || [];
      let prevCoords = null;

      enrichedHops.forEach((hop, index) => {
        if (!hop.geo || !hop.geo.latitude || !hop.geo.longitude) return;

        const coords = [hop.geo.latitude, hop.geo.longitude];
        
        // Determine marker color based on infrastructure type
        let markerColor = this.config.hop_marker_color;
        let markerIcon = '🔵';
        
        if (hop.infrastructure) {
          if (hop.infrastructure.is_ixp) {
            markerColor = this.config.ixp_marker_color;
            markerIcon = '🔗';
          } else if (hop.infrastructure.is_datacenter) {
            markerColor = PROVIDER_COLORS.datacenter;
            markerIcon = '🏢';
          } else if (hop.asn && hop.asn.provider_type) {
            markerColor = PROVIDER_COLORS[hop.asn.provider_type] || PROVIDER_COLORS.unknown;
            markerIcon = hop.asn.provider_type === 'cloud' ? '☁️' : 
                        hop.asn.provider_type === 'cdn' ? '⚡' :
                        hop.asn.provider_type === 'transit' ? '🌐' : '📍';
          }
        }

        // Add hop marker
        const hopMarker = this._addHopMarker(coords, hop, markerColor, markerIcon);
        this._enrichedHopMarkers.push(hopMarker);

        // Draw path segment to previous hop
        if (prevCoords && this.config.show_path_details) {
          const segmentColor = this._getSegmentColor(hop);
          const segment = L.polyline([prevCoords, coords], {
            color: segmentColor,
            weight: 3,
            opacity: 0.8,
            dashArray: hop.asn ? null : '5, 5',
          }).addTo(this._map);
          
          this._polylines.push(segment);
        }

        prevCoords = coords;
      });
    });
  }

  _addHopMarker(coords, hop, color, icon) {
    const marker = L.circleMarker(coords, {
      radius: 6,
      fillColor: color,
      color: '#fff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.8,
    }).addTo(this._map);

    // Build popup content
    let popupHtml = `<div class="popup-content">`;
    popupHtml += `<h4>${icon} Hop ${hop.hop_number}</h4>`;
    popupHtml += `<p><strong>IP:</strong> ${hop.ip_address || 'Unknown'}</p>`;
    
    if (hop.rtt_ms) {
      popupHtml += `<p><strong>RTT:</strong> ${hop.rtt_ms.toFixed(1)} ms</p>`;
    }
    
    if (hop.geo) {
      popupHtml += `<p><strong>Location:</strong> ${hop.geo.city || '?'}, ${hop.geo.country || '?'}</p>`;
      if (hop.geo.isp) {
        popupHtml += `<p><strong>ISP:</strong> ${hop.geo.isp}</p>`;
      }
    }
    
    if (hop.asn) {
      popupHtml += `<p><strong>ASN:</strong> AS${hop.asn.asn} (${hop.asn.name || 'Unknown'})</p>`;
      if (hop.asn.provider_type) {
        popupHtml += `<p><strong>Type:</strong> ${hop.asn.provider_type}</p>`;
      }
    }
    
    if (hop.infrastructure) {
      if (hop.infrastructure.is_ixp) {
        popupHtml += `<p><strong>🔗 IXP:</strong> ${hop.infrastructure.ixp_name || 'Internet Exchange'}</p>`;
      }
      if (hop.infrastructure.is_datacenter) {
        popupHtml += `<p><strong>🏢 Datacenter:</strong> ${hop.infrastructure.datacenter_name || 'Data Center'}</p>`;
      }
    }
    
    popupHtml += `</div>`;
    marker.bindPopup(popupHtml);
    
    return marker;
  }

  _getSegmentColor(hop) {
    if (hop.infrastructure?.is_ixp) return PROVIDER_COLORS.ixp;
    if (hop.asn?.provider_type) return PROVIDER_COLORS[hop.asn.provider_type] || this.config.link_color;
    return this.config.link_color;
  }

  _updatePathSummary(traceroutes) {
    const summaryPanel = this.shadowRoot.getElementById('path-summary-panel');
    const asnPath = this.shadowRoot.getElementById('asn-path');
    const pathStats = this.shadowRoot.getElementById('path-stats');
    
    // Get the first (or most recent) traceroute with a path summary
    let pathSummary = null;
    for (const trace of Object.values(traceroutes)) {
      if (trace.path_summary) {
        pathSummary = trace.path_summary;
        break;
      }
    }

    if (!pathSummary) {
      summaryPanel.style.display = 'none';
      return;
    }

    summaryPanel.style.display = 'block';

    // Build ASN path visualization
    const asnTransitions = pathSummary.asn_path || [];
    let asnHtml = '';
    asnTransitions.forEach((asn, i) => {
      const color = this._getAsnColor(asn);
      asnHtml += `<span class="asn-badge" style="background: ${color}">AS${asn.asn} ${asn.name || ''}</span>`;
      if (i < asnTransitions.length - 1) {
        asnHtml += `<span class="asn-arrow">→</span>`;
      }
    });
    asnPath.innerHTML = asnHtml;

    // Build path statistics
    let statsHtml = '';
    
    if (pathSummary.total_hops !== undefined) {
      statsHtml += `
        <div class="path-stat">
          <div class="path-stat-value">${pathSummary.total_hops}</div>
          <div class="path-stat-label">Total Hops</div>
        </div>
      `;
    }
    
    if (pathSummary.asn_count !== undefined) {
      statsHtml += `
        <div class="path-stat">
          <div class="path-stat-value">${pathSummary.asn_count}</div>
          <div class="path-stat-label">ASNs Traversed</div>
        </div>
      `;
    }
    
    if (pathSummary.country_count !== undefined) {
      statsHtml += `
        <div class="path-stat">
          <div class="path-stat-value">${pathSummary.country_count}</div>
          <div class="path-stat-label">Countries</div>
        </div>
      `;
    }
    
    if (pathSummary.ixp_count !== undefined && pathSummary.ixp_count > 0) {
      statsHtml += `
        <div class="path-stat">
          <div class="path-stat-value">${pathSummary.ixp_count}</div>
          <div class="path-stat-label">IXPs</div>
        </div>
      `;
    }
    
    pathStats.innerHTML = statsHtml;
  }

  _getAsnColor(asn) {
    if (asn.provider_type) return PROVIDER_COLORS[asn.provider_type];
    return PROVIDER_COLORS.unknown;
  }

  _addMarker(lat, lng, name, isMe, data) {
    const color = isMe ? this.config.my_marker_color : this.config.marker_color;
    
    const icon = L.divIcon({
      className: 'custom-marker',
      html: `
        <div style="
          background: ${color};
          width: 24px;
          height: 24px;
          border-radius: 50%;
          border: 3px solid white;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
          display: flex;
          align-items: center;
          justify-content: center;
        ">
          <span style="color: white; font-size: 12px;">🏠</span>
        </div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    const marker = L.marker([lat, lng], { icon }).addTo(this._map);
    
    // Create popup content
    const popupContent = this._createPopupContent(name, isMe, data);
    marker.bindPopup(popupContent);
    
    this._markers.push(marker);
    return marker;
  }

  _createPopupContent(name, isMe, data) {
    const statusClass = data.online ? 'online' : 'offline';
    const statusText = data.online ? 'Online' : 'Offline';
    
    return `
      <div class="popup-content">
        <h4>${isMe ? '🏠 ' : ''}${name}</h4>
        <p><span class="status ${statusClass}">${statusText}</span></p>
        ${data.public_ip ? `<p>IP: ${data.public_ip}</p>` : ''}
        ${data.version ? `<p>Version: ${data.version}</p>` : ''}
        ${data.last_seen ? `<p>Last seen: ${new Date(data.last_seen).toLocaleString()}</p>` : ''}
        ${!isMe ? `<p><button onclick="window.dispatchEvent(new CustomEvent('haimish-traceroute', {detail: '${data.peer_id}'}))">Traceroute</button></p>` : ''}
      </div>
    `;
  }

  _drawTopologyLinks(links, peers, myLocation, myPeerId) {
    // Create a map of peer_id to location
    const peerLocations = {};
    
    if (myPeerId && myLocation.latitude && myLocation.longitude) {
      peerLocations[myPeerId] = [myLocation.latitude, myLocation.longitude];
    }
    
    peers.forEach(peer => {
      if (peer.peer_id && peer.latitude && peer.longitude) {
        peerLocations[peer.peer_id] = [peer.latitude, peer.longitude];
      }
    });

    // Draw links
    links.forEach(link => {
      const sourceCoords = peerLocations[link.source];
      const targetCoords = peerLocations[link.target];
      
      if (sourceCoords && targetCoords) {
        const polyline = L.polyline([sourceCoords, targetCoords], {
          color: this.config.link_color,
          weight: 2,
          opacity: 0.7,
          dashArray: link.latency_ms ? null : '5, 10', // Dashed if no latency data
        }).addTo(this._map);
        
        // Add popup with link info
        if (link.latency_ms || link.hop_count) {
          polyline.bindPopup(`
            <div class="popup-content">
              <h4>Network Path</h4>
              ${link.latency_ms ? `<p>Latency: ${link.latency_ms.toFixed(1)} ms</p>` : ''}
              ${link.hop_count ? `<p>Hops: ${link.hop_count}</p>` : ''}
              ${link.last_measured ? `<p>Measured: ${new Date(link.last_measured).toLocaleString()}</p>` : ''}
            </div>
          `);
        }
        
        this._polylines.push(polyline);
      }
    });
  }

  _clearMapLayers() {
    this._markers.forEach(marker => marker.remove());
    this._markers = [];
    
    this._polylines.forEach(line => line.remove());
    this._polylines = [];
    
    // Clear enriched hop markers
    if (this._enrichedHopMarkers) {
      this._enrichedHopMarkers.forEach(m => m.remove());
      this._enrichedHopMarkers = [];
    }
  }

  _updateStatus(status) {
    const statusEl = this.shadowRoot.getElementById('status');
    if (statusEl) {
      statusEl.textContent = status;
    }
  }

  _callService(service, data = {}) {
    if (!this._hass) return;
    
    this._hass.callService('haimish', service, data);
  }

  _renderError(error) {
    this.shadowRoot.innerHTML = `
      <ha-card>
        <div style="padding: 16px; color: red;">
          Error loading HAIMish Map: ${error.message}
        </div>
      </ha-card>
    `;
  }

  getCardSize() {
    return 5;
  }

  static getConfigElement() {
    return document.createElement('haimish-map-editor');
  }

  static getStubConfig() {
    return {
      entity: 'sensor.haimish_network_topology',
      title: 'HAIMish',
      height: '400px',
    };
  }
}

// Card Editor
class HAIMishMapEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  _render() {
    this.innerHTML = `
      <style>
        .form-group {
          margin: 16px 0;
        }
        label {
          display: block;
          margin-bottom: 4px;
          font-weight: 500;
        }
        input[type="text"], input[type="number"], select {
          width: 100%;
          padding: 8px;
          border: 1px solid #ccc;
          border-radius: 4px;
        }
        .checkbox-group {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .checkbox-group input {
          width: auto;
        }
        .section-title {
          font-weight: 600;
          margin-top: 20px;
          margin-bottom: 8px;
          padding-bottom: 4px;
          border-bottom: 1px solid #eee;
        }
      </style>
      <div class="form-group">
        <label>Entity</label>
        <input type="text" id="entity" value="${this._config.entity || ''}">
      </div>
      <div class="form-group">
        <label>Title</label>
        <input type="text" id="title" value="${this._config.title || 'HAIMish'}">
      </div>
      <div class="form-group">
        <label>Height</label>
        <input type="text" id="height" value="${this._config.height || '400px'}">
      </div>
      <div class="form-group">
        <label>Default Zoom</label>
        <input type="number" id="zoom" value="${this._config.zoom || 4}" min="1" max="18">
      </div>
      
      <div class="section-title">Display Options</div>
      <div class="form-group checkbox-group">
        <input type="checkbox" id="show_topology" ${this._config.show_topology !== false ? 'checked' : ''}>
        <label for="show_topology">Show Network Topology</label>
      </div>
      <div class="form-group checkbox-group">
        <input type="checkbox" id="show_traceroute" ${this._config.show_traceroute !== false ? 'checked' : ''}>
        <label for="show_traceroute">Show Traceroutes</label>
      </div>
      <div class="form-group checkbox-group">
        <input type="checkbox" id="show_enriched_hops" ${this._config.show_enriched_hops !== false ? 'checked' : ''}>
        <label for="show_enriched_hops">Show Intermediate Hops</label>
      </div>
      
      <div class="section-title">Live Features</div>
      <div class="form-group checkbox-group">
        <input type="checkbox" id="show_live_activity" ${this._config.show_live_activity !== false ? 'checked' : ''}>
        <label for="show_live_activity">Show Live Activity Feed</label>
      </div>
      <div class="form-group checkbox-group">
        <input type="checkbox" id="animate_new_data" ${this._config.animate_new_data !== false ? 'checked' : ''}>
        <label for="animate_new_data">Animate New Data</label>
      </div>
    `;

    // Add event listeners for text/number inputs
    ['entity', 'title', 'height', 'zoom'].forEach(field => {
      this.querySelector(`#${field}`).addEventListener('change', (e) => {
        this._config = { ...this._config, [field]: e.target.value };
        this._fireConfigChanged();
      });
    });
    
    // Add event listeners for checkboxes
    ['show_topology', 'show_traceroute', 'show_enriched_hops', 'show_live_activity', 'animate_new_data'].forEach(field => {
      this.querySelector(`#${field}`).addEventListener('change', (e) => {
        this._config = { ...this._config, [field]: e.target.checked };
        this._fireConfigChanged();
      });
    });
  }

  _fireConfigChanged() {
    const event = new CustomEvent('config-changed', {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

// Register custom elements
customElements.define('haimish-map', HAIMishMapCard);
customElements.define('haimish-map-editor', HAIMishMapEditor);

// Register card with Home Assistant
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'haimish-map',
  name: 'HAIMish Map',
  description: 'Display Home Assistant community deployments on a map with network topology',
  preview: true,
  documentationURL: 'https://github.com/jaylouisw/HA',
});

console.info(
  `%c HAIMISH-MAP %c v${CARD_VERSION} `,
  'background: #03a9f4; color: white; font-weight: bold;',
  'background: #333; color: white;'
);
