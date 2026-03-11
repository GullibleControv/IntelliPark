/**
 * IntelliPark Admin Panel Logic
 */

let polygonDrawer = null;
let currentVideoSourceId = null;
let frameData = null;

document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication
    if (!api.isAuthenticated()) {
        window.location.href = 'login.html?return=' + encodeURIComponent(window.location.href);
        return;
    }

    initializeUI();
    await loadExistingData();
});

/**
 * Initialize UI elements and event listeners
 */
function initializeUI() {
    // Step 1: Extract Frame
    document.getElementById('btn-extract-frame').addEventListener('click', handleExtractFrame);

    // Step 2: Drawing tools
    document.getElementById('btn-undo').addEventListener('click', () => {
        polygonDrawer?.undoLastPoint();
    });

    document.getElementById('btn-clear-current').addEventListener('click', () => {
        polygonDrawer?.cancelCurrentPolygon();
    });

    document.getElementById('btn-delete-selected').addEventListener('click', () => {
        polygonDrawer?.deleteSelected();
    });

    document.getElementById('btn-back').addEventListener('click', () => {
        document.getElementById('step-draw').style.display = 'none';
        document.getElementById('step-video').style.display = 'block';
    });

    document.getElementById('btn-save-spaces').addEventListener('click', handleSaveSpaces);

    // Detection control
    document.getElementById('select-source').addEventListener('change', (e) => {
        document.getElementById('btn-get-config').disabled = !e.target.value;
    });

    document.getElementById('btn-get-config').addEventListener('click', handleGetDetectionConfig);

    // Filter and refresh
    document.getElementById('filter-location').addEventListener('change', (e) => {
        loadSpacesList(e.target.value);
    });

    document.getElementById('btn-refresh-spaces').addEventListener('click', () => {
        loadSpacesList(document.getElementById('filter-location').value);
    });
}

/**
 * Load existing data (video sources, spaces, locations)
 */
async function loadExistingData() {
    try {
        // Load locations for filter
        const locationsResponse = await api.getLocations();
        const locationSelect = document.getElementById('filter-location');
        locationsResponse.locations.forEach(loc => {
            const option = document.createElement('option');
            option.value = loc;
            option.textContent = loc;
            locationSelect.appendChild(option);
        });

        // Load video sources
        await loadVideoSources();

        // Load spaces list
        await loadSpacesList();

    } catch (error) {
        console.error('Failed to load data:', error);
    }
}

/**
 * Load video sources for detection
 */
async function loadVideoSources() {
    try {
        const response = await api.request('/admin/video-sources');
        const select = document.getElementById('select-source');

        select.innerHTML = '<option value="">Select Video Source</option>';

        response.sources.forEach(source => {
            const option = document.createElement('option');
            option.value = source.id;
            option.textContent = `${source.name} (${source.location})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load video sources:', error);
    }
}

/**
 * Handle frame extraction from YouTube URL
 */
async function handleExtractFrame() {
    const urlInput = document.getElementById('youtube-url');
    const locationInput = document.getElementById('location-name');
    const button = document.getElementById('btn-extract-frame');

    const url = urlInput.value.trim();
    const location = locationInput.value.trim();

    if (!url) {
        showError('Please enter a YouTube URL');
        return;
    }

    if (!location) {
        showError('Please enter a location name');
        return;
    }

    button.disabled = true;
    button.textContent = 'Extracting Frame... (this may take a minute)';

    try {
        const response = await api.request('/admin/extract-frame', {
            method: 'POST',
            body: JSON.stringify({ url })
        });

        frameData = {
            image: response.frame,
            width: response.width,
            height: response.height,
            url: url,
            location: location
        };

        // Create video source record
        const sourceResponse = await api.request('/admin/video-sources', {
            method: 'POST',
            body: JSON.stringify({
                name: `${location} Camera`,
                url: url,
                location: location,
                frame_width: response.width,
                frame_height: response.height
            })
        });

        currentVideoSourceId = sourceResponse.source.id;

        // Initialize polygon drawer
        initializeDrawingCanvas();

        // Show drawing step
        document.getElementById('step-video').style.display = 'none';
        document.getElementById('step-draw').style.display = 'block';

        showSuccess('Frame extracted successfully. Start drawing parking spaces.');

    } catch (error) {
        showError(error.message || 'Failed to extract frame. Make sure the URL is valid.');
    } finally {
        button.disabled = false;
        button.textContent = 'Extract Frame';
    }
}

/**
 * Initialize the drawing canvas with the extracted frame
 */
function initializeDrawingCanvas() {
    polygonDrawer = new PolygonDrawer('drawing-canvas', {
        onPolygonComplete: (polygon, index) => {
            updateToolbarState();
            updatePolygonCount();
        },
        onPolygonSelect: (polygon, index) => {
            document.getElementById('btn-delete-selected').disabled = index === -1;
        },
        onChange: (state) => {
            updateToolbarState();
            updatePolygonCount();
        }
    });

    polygonDrawer.setBackgroundImage(
        frameData.image,
        frameData.width,
        frameData.height
    );
}

/**
 * Update toolbar button states
 */
function updateToolbarState() {
    const isDrawing = polygonDrawer?.isDrawing() || false;
    const hasPolygons = polygonDrawer?.getPolygonCount() > 0 || false;

    document.getElementById('btn-undo').disabled = !isDrawing;
    document.getElementById('btn-clear-current').disabled = !isDrawing;
    document.getElementById('btn-save-spaces').disabled = !hasPolygons;
}

/**
 * Update polygon count display
 */
function updatePolygonCount() {
    const count = polygonDrawer?.getPolygonCount() || 0;
    document.getElementById('polygon-count').textContent = count;
}

/**
 * Save drawn parking spaces
 */
async function handleSaveSpaces() {
    if (!polygonDrawer || polygonDrawer.getPolygonCount() === 0) {
        showError('No parking spaces to save');
        return;
    }

    const button = document.getElementById('btn-save-spaces');
    button.disabled = true;
    button.textContent = 'Saving...';

    try {
        const polygons = polygonDrawer.getPolygonsForSave();

        const response = await api.request('/admin/spaces/bulk', {
            method: 'POST',
            body: JSON.stringify({
                location: frameData.location,
                spaces: polygons.map(p => ({
                    name: p.name,
                    coordinates: p.coordinates
                }))
            })
        });

        showSuccess(`Saved ${response.spaces.length} parking spaces`);

        // Reload video sources and spaces list
        await loadVideoSources();
        await loadSpacesList();

        // Reset drawing
        polygonDrawer.reset();
        document.getElementById('step-draw').style.display = 'none';
        document.getElementById('step-video').style.display = 'block';
        document.getElementById('youtube-url').value = '';
        document.getElementById('location-name').value = '';

    } catch (error) {
        showError(error.message || 'Failed to save parking spaces');
    } finally {
        button.disabled = false;
        button.textContent = 'Save Parking Spaces';
    }
}

/**
 * Load and display existing parking spaces
 */
async function loadSpacesList(location = '') {
    const container = document.getElementById('spaces-list');
    container.innerHTML = '<p class="loading-state">Loading...</p>';

    try {
        const query = location ? `?location=${encodeURIComponent(location)}` : '';
        const response = await api.request(`/admin/spaces-with-coordinates${query}`);

        if (response.spaces.length === 0) {
            container.innerHTML = '<p class="empty-state">No parking spaces configured yet. Use the form above to add spaces.</p>';
            return;
        }

        container.innerHTML = '';

        response.spaces.forEach(space => {
            const card = document.createElement('div');
            card.className = 'space-item';
            card.innerHTML = `
                <div class="space-info">
                    <span class="space-name">${escapeHtml(space.name)}</span>
                    <span class="space-location">${escapeHtml(space.location)}</span>
                </div>
                <div class="space-meta">
                    <span>Floor: ${space.floor}</span>
                    <span>Type: ${space.vehicle_type}</span>
                    <span>Rs. ${space.hourly_rate}/hr</span>
                    <span>${space.coordinates?.length || 0} points</span>
                </div>
                <div class="space-actions">
                    <button class="btn btn-sm btn-danger" onclick="deleteSpace(${space.id})">Delete</button>
                </div>
            `;
            container.appendChild(card);
        });

    } catch (error) {
        container.innerHTML = '<p class="error-state">Failed to load spaces</p>';
    }
}

/**
 * Delete a parking space
 */
async function deleteSpace(spaceId) {
    if (!confirm('Are you sure you want to delete this parking space?')) {
        return;
    }

    try {
        await api.request(`/parking/spaces/${spaceId}`, {
            method: 'DELETE'
        });

        showSuccess('Parking space deleted');
        await loadSpacesList(document.getElementById('filter-location').value);

    } catch (error) {
        showError(error.message || 'Failed to delete space');
    }
}

/**
 * Get detection command for selected video source
 */
async function handleGetDetectionConfig() {
    const sourceId = document.getElementById('select-source').value;

    if (!sourceId) {
        showError('Please select a video source');
        return;
    }

    try {
        const response = await api.request(`/admin/detection/config?source_id=${sourceId}`);

        const commandDiv = document.getElementById('detection-command');
        const commandText = document.getElementById('command-text');

        commandText.textContent = response.command;
        commandDiv.style.display = 'block';

        showSuccess(`Detection configured for ${response.source.name}. ${response.spaces_count} spaces available.`);

    } catch (error) {
        showError(error.message || 'Failed to get detection config');
    }
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
 * Show error message
 */
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    const successDiv = document.getElementById('success-message');
    successDiv.style.display = 'none';
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

/**
 * Show success message
 */
function showSuccess(message) {
    const successDiv = document.getElementById('success-message');
    const errorDiv = document.getElementById('error-message');
    errorDiv.style.display = 'none';
    successDiv.textContent = message;
    successDiv.style.display = 'block';
    setTimeout(() => {
        successDiv.style.display = 'none';
    }, 5000);
}
