/**
 * IntelliPark Live Detection Dashboard
 * Real-time parking status monitoring with WebSocket updates
 * Professional UI with clean animations
 */

// Auto-detect API URL based on environment
const API_BASE_URL = window.INTELLIPARK_API_URL ||
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://localhost:5000'
        : window.location.origin);
let socket = null;
let currentLocation = '';
let activityCount = 0;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initWebSocket();
    loadInitialData();
    setupEventListeners();
});

/**
 * Initialize WebSocket connection for real-time updates
 */
function initWebSocket() {
    updateConnectionStatus('connecting');

    try {
        socket = io(API_BASE_URL, {
            transports: ['websocket', 'polling'],
            reconnectionAttempts: 5,
            reconnectionDelay: 1000
        });

        socket.on('connect', () => {
            console.log('WebSocket connected');
            updateConnectionStatus('connected');
            addLog('info', 'Connected to IntelliPark server');

            // Subscribe to updates
            if (currentLocation) {
                socket.emit('subscribe_location', { location: currentLocation });
            }
        });

        socket.on('disconnect', () => {
            console.log('WebSocket disconnected');
            updateConnectionStatus('disconnected');
            addLog('warning', 'Disconnected from server');
        });

        socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            updateConnectionStatus('disconnected');
            addLog('error', 'Connection failed - is the backend running?');
        });

        // Listen for space updates
        socket.on('space_update', (data) => {
            console.log('Space update received:', data);
            handleSpaceUpdate(data);
        });

        // Listen for occupancy summary
        socket.on('occupancy_summary', (data) => {
            console.log('Occupancy summary received:', data);
            updateStats(data);
        });

    } catch (error) {
        console.error('Failed to initialize WebSocket:', error);
        updateConnectionStatus('disconnected');
        addLog('error', 'Failed to initialize WebSocket connection');
    }
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus(status) {
    const statusEl = document.getElementById('connectionStatus');
    const dot = statusEl.querySelector('.pulse-dot');
    const text = statusEl.querySelector('.status-text');

    // Remove all status classes
    statusEl.classList.remove('connected', 'disconnected');

    switch (status) {
        case 'connected':
            statusEl.classList.add('connected');
            text.textContent = 'Live';
            break;
        case 'connecting':
            text.textContent = 'Connecting...';
            break;
        case 'disconnected':
            statusEl.classList.add('disconnected');
            text.textContent = 'Offline';
            break;
    }
}

/**
 * Load initial data from API
 */
async function loadInitialData() {
    try {
        // Load parking spaces
        await loadParkingSpaces();

        // Load video sources for dropdown
        await loadVideoSources();

        // Load locations for filter
        await loadLocations();

        // Load overall status
        await loadOverallStatus();

        addLog('info', 'Dashboard initialized successfully');
    } catch (error) {
        console.error('Error loading initial data:', error);
        addLog('error', 'Failed to load initial data');
    }
}

/**
 * Load parking spaces and render the map
 */
async function loadParkingSpaces() {
    const mapEl = document.getElementById('parkingMap');

    try {
        let url = `${API_BASE_URL}/api/parking/spaces`;
        if (currentLocation) {
            url += `?location=${encodeURIComponent(currentLocation)}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        const spaces = data.spaces || [];

        if (spaces.length === 0) {
            mapEl.innerHTML = `
                <div class="empty-state" style="grid-column: 1 / -1;">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <rect x="3" y="3" width="18" height="18" rx="2"/>
                        <path d="M9 17V7h4a3 3 0 010 6H9"/>
                    </svg>
                    <p>No parking spaces configured</p>
                    <a href="admin.html" style="color: var(--primary-color); font-weight: 500;">Go to Admin Panel</a>
                </div>
            `;
            return;
        }

        mapEl.innerHTML = spaces.map(space => `
            <div class="parking-space ${space.is_occupied ? 'occupied' : 'available'}"
                 data-space-id="${space.id}"
                 title="${escapeHtml(space.name)} - ${escapeHtml(space.location)}">
                <span class="space-name">${escapeHtml(space.name)}</span>
                <span class="space-status">${space.is_occupied ? 'Occupied' : 'Free'}</span>
                <span class="space-location">${escapeHtml(truncateLocation(space.location))}</span>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading parking spaces:', error);
        mapEl.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <p style="color: var(--danger-color);">Failed to load parking spaces</p>
            </div>
        `;
    }
}

/**
 * Truncate long location names
 */
function truncateLocation(location) {
    if (location.length > 15) {
        return location.substring(0, 12) + '...';
    }
    return location;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Load video sources for detection command
 */
async function loadVideoSources() {
    const selectEl = document.getElementById('videoSource');

    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/video-sources`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) {
            selectEl.innerHTML = '<option value="">Login as admin to see video sources</option>';
            return;
        }

        const data = await response.json();
        const sources = data.sources || [];

        selectEl.innerHTML = '<option value="">Select a video source...</option>';
        sources.forEach(source => {
            selectEl.innerHTML += `<option value="${source.id}" data-url="${escapeHtml(source.url)}" data-location="${escapeHtml(source.location)}">
                ${escapeHtml(source.name)} (${escapeHtml(source.location)})
            </option>`;
        });

    } catch (error) {
        console.error('Error loading video sources:', error);
        selectEl.innerHTML = '<option value="">Unable to load video sources</option>';
    }
}

/**
 * Load locations for filter dropdown
 */
async function loadLocations() {
    const selectEl = document.getElementById('locationFilter');

    try {
        const response = await fetch(`${API_BASE_URL}/api/parking/locations`);
        const data = await response.json();

        const locations = data.locations || [];

        selectEl.innerHTML = '<option value="">All Locations</option>';
        locations.forEach(loc => {
            selectEl.innerHTML += `<option value="${escapeHtml(loc)}">${escapeHtml(loc)}</option>`;
        });

    } catch (error) {
        console.error('Error loading locations:', error);
    }
}

/**
 * Load overall occupancy status
 */
async function loadOverallStatus() {
    try {
        let url = `${API_BASE_URL}/api/parking/status`;
        if (currentLocation) {
            url += `?location=${encodeURIComponent(currentLocation)}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        updateStats(data);

    } catch (error) {
        console.error('Error loading status:', error);
    }
}

/**
 * Update statistics display
 */
function updateStats(data) {
    const total = data.total || 0;
    const occupied = data.occupied || 0;
    const available = total - occupied;
    const rate = total > 0 ? Math.round((occupied / total) * 100) : 0;

    // Update stat cards with animation
    animateValue('totalSpaces', total);
    animateValue('availableSpaces', available);
    animateValue('occupiedSpaces', occupied);
    document.getElementById('occupancyRate').textContent = `${rate}%`;

    // Update progress bar
    const fillEl = document.getElementById('occupancyFill');
    const labelEl = document.getElementById('occupancyLabel');

    fillEl.style.width = `${rate}%`;
    labelEl.textContent = `${rate}%`;

    // Update progress bar color based on occupancy level
    if (rate >= 80) {
        fillEl.style.background = `linear-gradient(90deg, #f87171 0%, #ef4444 100%)`;
    } else if (rate >= 50) {
        fillEl.style.background = `linear-gradient(90deg, #fbbf24 0%, #f59e0b 100%)`;
    } else {
        fillEl.style.background = `linear-gradient(90deg, #34d399 0%, #10b981 100%)`;
    }
}

/**
 * Animate number value change
 */
function animateValue(elementId, newValue) {
    const el = document.getElementById(elementId);
    const currentValue = parseInt(el.textContent) || 0;

    if (currentValue === newValue) return;

    el.textContent = newValue;
    el.style.transform = 'scale(1.1)';
    setTimeout(() => {
        el.style.transform = 'scale(1)';
    }, 200);
}

/**
 * Handle real-time space update
 */
function handleSpaceUpdate(data) {
    const spaceId = data.space_id;
    const isOccupied = data.is_occupied;

    // Update the space element in the map
    const spaceEl = document.querySelector(`[data-space-id="${spaceId}"]`);
    if (spaceEl) {
        spaceEl.className = `parking-space ${isOccupied ? 'occupied' : 'available'}`;
        spaceEl.querySelector('.space-status').textContent = isOccupied ? 'Occupied' : 'Free';

        // Add flash animation
        spaceEl.style.animation = 'none';
        spaceEl.offsetHeight; // Trigger reflow
        spaceEl.style.animation = 'flash 0.5s ease-out';
    }

    // Add activity item
    addActivity(
        isOccupied,
        `Space ${data.space_id}`,
        isOccupied ? 'Vehicle parked' : 'Space freed',
        data.confidence ? `${(data.confidence * 100).toFixed(0)}% confidence` : ''
    );

    // Add log entry
    addLog('update', `Space ${spaceId}: ${isOccupied ? 'OCCUPIED' : 'AVAILABLE'}`);

    // Refresh overall status
    loadOverallStatus();
}

/**
 * Add activity item to feed
 */
function addActivity(isOccupied, title, message, extra = '') {
    const feedEl = document.getElementById('activityFeed');

    // Remove empty state if exists
    const emptyState = feedEl.querySelector('.empty-state');
    if (emptyState) emptyState.remove();

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const statusClass = isOccupied ? 'occupied' : 'available';
    const icon = isOccupied ?
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/></svg>' :
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';

    const itemHTML = `
        <div class="activity-item ${statusClass}">
            <div class="activity-icon">${icon}</div>
            <div class="activity-content">
                <strong>${escapeHtml(title)}</strong>
                <p>${escapeHtml(message)}${extra ? ` - ${escapeHtml(extra)}` : ''}</p>
            </div>
            <span class="activity-time">${time}</span>
        </div>
    `;

    feedEl.insertAdjacentHTML('afterbegin', itemHTML);

    // Update activity count
    activityCount++;
    document.getElementById('activityCount').textContent = activityCount;

    // Limit to 20 items
    const items = feedEl.querySelectorAll('.activity-item');
    if (items.length > 20) {
        items[items.length - 1].remove();
    }
}

/**
 * Add log entry
 */
function addLog(level, message) {
    const logsEl = document.getElementById('logsContainer');
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const badgeText = level.toUpperCase();

    const logHTML = `
        <div class="log-entry ${level}">
            <span class="log-time">${time}</span>
            <span class="log-badge ${level}">${badgeText}</span>
            <span class="log-message">${escapeHtml(message)}</span>
        </div>
    `;

    logsEl.insertAdjacentHTML('afterbegin', logHTML);

    // Limit to 50 entries
    const entries = logsEl.querySelectorAll('.log-entry');
    if (entries.length > 50) {
        entries[entries.length - 1].remove();
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Location filter
    document.getElementById('locationFilter').addEventListener('change', (e) => {
        currentLocation = e.target.value;
        loadParkingSpaces();
        loadOverallStatus();

        // Update WebSocket subscription
        if (socket && socket.connected) {
            if (currentLocation) {
                socket.emit('subscribe_location', { location: currentLocation });
            }
        }
    });

    // Video source selection
    document.getElementById('videoSource').addEventListener('change', (e) => {
        const select = e.target;
        const selectedOption = select.options[select.selectedIndex];
        const url = selectedOption.dataset.url;
        const location = selectedOption.dataset.location;

        updateDetectionCommand(url, location);
    });

    // Refresh button
    document.getElementById('refreshBtn').addEventListener('click', () => {
        const btn = document.getElementById('refreshBtn');
        btn.disabled = true;

        loadParkingSpaces();
        loadOverallStatus();
        addLog('info', 'Status refreshed');

        setTimeout(() => {
            btn.disabled = false;
        }, 1000);
    });

    // Copy command button
    document.getElementById('copyCommand').addEventListener('click', () => {
        const code = document.getElementById('commandCode').textContent;
        navigator.clipboard.writeText(code).then(() => {
            const btn = document.getElementById('copyCommand');
            const originalHTML = btn.innerHTML;
            btn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"/>
                </svg>
                Copied!
            `;
            setTimeout(() => {
                btn.innerHTML = originalHTML;
            }, 2000);
        });
    });

    // Clear logs button
    const clearLogsBtn = document.getElementById('clearLogs');
    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', () => {
            const logsEl = document.getElementById('logsContainer');
            logsEl.innerHTML = `
                <div class="log-entry info">
                    <span class="log-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                    <span class="log-badge info">INFO</span>
                    <span class="log-message">Logs cleared</span>
                </div>
            `;
        });
    }
}

/**
 * Update detection command display
 */
function updateDetectionCommand(url, location) {
    const codeEl = document.getElementById('commandCode');

    if (!url) {
        codeEl.textContent = 'Select a video source to see the detection command';
        return;
    }

    const command = `cd detection && python detector.py --source "${url}" --speed 0.25`;
    codeEl.textContent = command;
}

// Add CSS animation for flash effect
const style = document.createElement('style');
style.textContent = `
    @keyframes flash {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.6; transform: scale(1.02); box-shadow: 0 0 20px rgba(0, 214, 125, 0.4); }
        100% { opacity: 1; transform: scale(1); }
    }

    .stat-value {
        transition: transform 0.2s ease;
    }
`;
document.head.appendChild(style);
