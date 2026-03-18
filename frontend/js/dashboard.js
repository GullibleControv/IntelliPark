/**
 * IntelliPark Live Detection Dashboard
 * Real-time parking status monitoring with WebSocket updates
 */

// Auto-detect API URL based on environment
const API_BASE_URL = window.INTELLIPARK_API_URL ||
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://localhost:5000'
        : window.location.origin);
let socket = null;
let currentLocation = '';
let activityLog = [];

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
    const dot = statusEl.querySelector('.status-dot');
    const text = statusEl.querySelector('span:last-child');

    dot.className = 'status-dot ' + (status === 'connected' ? 'connected' : 'disconnected');

    switch (status) {
        case 'connected':
            text.textContent = 'Live';
            break;
        case 'connecting':
            text.textContent = 'Connecting...';
            break;
        case 'disconnected':
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
                <div class="empty" style="grid-column: 1 / -1; text-align: center; padding: 2rem;">
                    <p>No parking spaces configured.</p>
                    <p style="color: #888; font-size: 0.9rem; margin-top: 0.5rem;">
                        Go to <a href="admin.html" style="color: #e94560;">Admin Panel</a> to add parking spaces.
                    </p>
                </div>
            `;
            return;
        }

        mapEl.innerHTML = spaces.map(space => `
            <div class="parking-space ${space.is_occupied ? 'occupied' : 'available'}"
                 data-space-id="${space.id}"
                 title="${space.name} - ${space.location}">
                <span class="space-name">${space.name}</span>
                <span class="space-status">${space.is_occupied ? '🚗' : '✅'}</span>
                <span class="space-location">${space.location.split(' - ')[0]}</span>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading parking spaces:', error);
        mapEl.innerHTML = '<p class="error">Failed to load parking spaces</p>';
    }
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
            // Not logged in or no admin access
            selectEl.innerHTML = '<option value="">Login as admin to see video sources</option>';
            return;
        }

        const data = await response.json();
        const sources = data.sources || [];

        selectEl.innerHTML = '<option value="">Select a video source...</option>';
        sources.forEach(source => {
            selectEl.innerHTML += `<option value="${source.id}" data-url="${source.url}" data-location="${source.location}">
                ${source.name} (${source.location})
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
            selectEl.innerHTML += `<option value="${loc}">${loc}</option>`;
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

    // Update stat cards
    document.getElementById('totalSpaces').textContent = total;
    document.getElementById('availableSpaces').textContent = available;
    document.getElementById('occupiedSpaces').textContent = occupied;
    document.getElementById('occupancyRate').textContent = `${rate}%`;

    // Update occupancy bar
    const fillEl = document.getElementById('occupancyFill');
    const labelEl = document.getElementById('occupancyLabel');

    fillEl.style.width = `${rate}%`;
    labelEl.textContent = `${rate}% Occupied`;

    // Change bar color based on occupancy
    if (rate >= 80) {
        fillEl.style.background = 'linear-gradient(90deg, #e94560, #ff6b6b)';
    } else if (rate >= 50) {
        fillEl.style.background = 'linear-gradient(90deg, #ffd700, #ffb700)';
    } else {
        fillEl.style.background = 'linear-gradient(90deg, #00ff88, #00cc6a)';
    }
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
        spaceEl.querySelector('.space-status').textContent = isOccupied ? '🚗' : '✅';

        // Add flash animation
        spaceEl.style.animation = 'none';
        setTimeout(() => {
            spaceEl.style.animation = 'flash 0.5s';
        }, 10);
    }

    // Add activity item
    addActivity(
        isOccupied ? '🚗' : '✅',
        `Space ${data.space_id} is now <strong>${isOccupied ? 'occupied' : 'available'}</strong>`,
        data.confidence ? `Confidence: ${(data.confidence * 100).toFixed(1)}%` : ''
    );

    // Add log entry
    addLog('update', `Space ${spaceId}: ${isOccupied ? 'OCCUPIED' : 'AVAILABLE'}`);

    // Refresh overall status
    loadOverallStatus();
}

/**
 * Add activity item to feed
 */
function addActivity(icon, message, extra = '') {
    const feedEl = document.getElementById('activityFeed');

    // Remove empty message if exists
    const emptyMsg = feedEl.querySelector('.empty');
    if (emptyMsg) emptyMsg.remove();

    const time = new Date().toLocaleTimeString();

    const itemHTML = `
        <div class="activity-item">
            <span class="activity-icon">${icon}</span>
            <div class="activity-content">
                <div>${message}</div>
                ${extra ? `<small style="color: #888;">${extra}</small>` : ''}
            </div>
            <span class="activity-time">${time}</span>
        </div>
    `;

    feedEl.insertAdjacentHTML('afterbegin', itemHTML);

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
    const time = new Date().toLocaleTimeString();

    const logHTML = `
        <div class="log-entry ${level}">
            <span class="log-time">${time}</span>
            <span class="log-message">${message}</span>
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
        loadParkingSpaces();
        loadOverallStatus();
        addLog('info', 'Status refreshed');
    });

    // Copy command button
    document.getElementById('copyCommand').addEventListener('click', () => {
        const code = document.getElementById('commandCode').textContent;
        navigator.clipboard.writeText(code).then(() => {
            const btn = document.getElementById('copyCommand');
            btn.textContent = '✓ Copied!';
            setTimeout(() => {
                btn.textContent = '📋 Copy';
            }, 2000);
        });
    });
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
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; transform: scale(1.05); }
    }
`;
document.head.appendChild(style);
