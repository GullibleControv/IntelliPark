/**
 * IntelliPark Parking Search Page Logic
 */

let selectedSpace = null;

document.addEventListener('DOMContentLoaded', async () => {
    await loadLocations();
    await loadSpaces();
    setupEventListeners();
});

/**
 * Load available locations
 */
async function loadLocations() {
    const locationSelect = document.getElementById('location-filter');
    if (!locationSelect) return;

    try {
        const response = await api.getLocations();
        const locations = response.locations || [];

        locations.forEach(location => {
            const option = document.createElement('option');
            option.value = location;
            option.textContent = location;
            locationSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load locations:', error);
    }
}

/**
 * Load parking spaces
 */
async function loadSpaces(filters = {}) {
    const container = document.getElementById('spaces-grid');
    const loadingDiv = document.getElementById('loading');
    const statusDiv = document.getElementById('status-summary');

    if (loadingDiv) loadingDiv.style.display = 'block';
    if (container) container.innerHTML = '';

    try {
        // Get spaces
        const spacesResponse = await api.getSpaces(filters);
        const spaces = spacesResponse.spaces || [];

        // Get status summary
        const statusResponse = await api.getParkingStatus(filters.location);

        if (loadingDiv) loadingDiv.style.display = 'none';

        // Update status summary
        if (statusDiv) {
            statusDiv.innerHTML = `
                <div class="status-item">
                    <span class="status-number">${statusResponse.total}</span>
                    <span class="status-label">Total Spots</span>
                </div>
                <div class="status-item available">
                    <span class="status-number">${statusResponse.available}</span>
                    <span class="status-label">Available</span>
                </div>
                <div class="status-item occupied">
                    <span class="status-number">${statusResponse.occupied}</span>
                    <span class="status-label">Occupied</span>
                </div>
            `;
        }

        // Display spaces
        if (spaces.length === 0) {
            container.innerHTML = '<p class="no-results">No parking spaces found.</p>';
            return;
        }

        spaces.forEach(space => {
            container.appendChild(createSpaceCard(space));
        });

    } catch (error) {
        if (loadingDiv) loadingDiv.style.display = 'none';
        showError(error.message || 'Failed to load parking spaces');
    }
}

/**
 * Create a space card element
 */
function createSpaceCard(space) {
    const card = document.createElement('div');
    card.className = `space-card ${space.is_occupied ? 'occupied' : 'available'}`;
    card.dataset.spaceId = space.id;

    card.innerHTML = `
        <div class="space-header">
            <h3>${escapeHtml(space.name)}</h3>
            <span class="space-status ${space.is_occupied ? 'occupied' : 'available'}">
                ${space.is_occupied ? 'Occupied' : 'Available'}
            </span>
        </div>
        <div class="space-details">
            <p class="space-location">${escapeHtml(space.location)}</p>
            <p class="space-floor">Floor: ${escapeHtml(space.floor)}</p>
            <p class="space-type">Type: ${escapeHtml(space.vehicle_type)}</p>
            <p class="space-rate">Rs. ${space.hourly_rate}/hour</p>
        </div>
        ${!space.is_occupied ? `
        <button class="btn btn-primary book-btn" onclick="selectSpace(${space.id})">
            Book Now
        </button>
        ` : ''}
    `;

    return card;
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Location filter
    const locationFilter = document.getElementById('location-filter');
    if (locationFilter) {
        locationFilter.addEventListener('change', (e) => {
            loadSpaces({ location: e.target.value || null, available: document.getElementById('available-only')?.checked });
        });
    }

    // Available only filter
    const availableFilter = document.getElementById('available-only');
    if (availableFilter) {
        availableFilter.addEventListener('change', (e) => {
            loadSpaces({
                location: document.getElementById('location-filter')?.value || null,
                available: e.target.checked
            });
        });
    }

    // Booking form
    const bookingForm = document.getElementById('booking-form');
    if (bookingForm) {
        bookingForm.addEventListener('submit', handleBooking);
    }

    // Close modal
    const closeModal = document.getElementById('close-modal');
    if (closeModal) {
        closeModal.addEventListener('click', hideBookingModal);
    }

    // Close modal on outside click
    const modal = document.getElementById('booking-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                hideBookingModal();
            }
        });
    }
}

/**
 * Select a space for booking
 */
async function selectSpace(spaceId) {
    // Check authentication
    if (!api.isAuthenticated()) {
        window.location.href = 'login.html?return=' + encodeURIComponent(window.location.href);
        return;
    }

    try {
        const response = await api.getSpace(spaceId);
        selectedSpace = response.space;
        showBookingModal(selectedSpace);
    } catch (error) {
        showError(error.message || 'Failed to load space details');
    }
}

/**
 * Show booking modal
 */
function showBookingModal(space) {
    const modal = document.getElementById('booking-modal');
    const spaceName = document.getElementById('modal-space-name');
    const spaceLocation = document.getElementById('modal-space-location');
    const spaceRate = document.getElementById('modal-space-rate');

    if (spaceName) spaceName.textContent = space.name;
    if (spaceLocation) spaceLocation.textContent = space.location;
    if (spaceRate) spaceRate.textContent = `Rs. ${space.hourly_rate}/hour`;

    // Set default dates
    const now = new Date();
    const startInput = document.getElementById('booking-start');
    const endInput = document.getElementById('booking-end');

    if (startInput) {
        const startDate = new Date(now.getTime() + 60 * 60 * 1000); // 1 hour from now
        startInput.value = formatDateTimeLocal(startDate);
    }

    if (endInput) {
        const endDate = new Date(now.getTime() + 3 * 60 * 60 * 1000); // 3 hours from now
        endInput.value = formatDateTimeLocal(endDate);
    }

    // Calculate initial estimate
    updatePriceEstimate();

    if (modal) {
        modal.style.display = 'flex';
    }
}

/**
 * Hide booking modal
 */
function hideBookingModal() {
    const modal = document.getElementById('booking-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    selectedSpace = null;
}

/**
 * Update price estimate
 */
function updatePriceEstimate() {
    const startInput = document.getElementById('booking-start');
    const endInput = document.getElementById('booking-end');
    const estimateDiv = document.getElementById('price-estimate');

    if (!startInput || !endInput || !selectedSpace || !estimateDiv) return;

    const start = new Date(startInput.value);
    const end = new Date(endInput.value);

    if (isNaN(start.getTime()) || isNaN(end.getTime())) {
        estimateDiv.textContent = '';
        return;
    }

    const hours = (end - start) / (1000 * 60 * 60);

    if (hours <= 0) {
        estimateDiv.textContent = 'End time must be after start time';
        return;
    }

    const total = hours * selectedSpace.hourly_rate;
    estimateDiv.textContent = `Estimated Total: Rs. ${total.toFixed(2)} (${hours.toFixed(1)} hours)`;
}

/**
 * Handle booking submission
 */
async function handleBooking(e) {
    e.preventDefault();

    if (!selectedSpace) {
        showError('Please select a parking space');
        return;
    }

    const startInput = document.getElementById('booking-start');
    const endInput = document.getElementById('booking-end');
    const vehicleInput = document.getElementById('vehicle-number');
    const submitBtn = e.target.querySelector('button[type="submit"]');

    const startTime = new Date(startInput.value).toISOString();
    const endTime = new Date(endInput.value).toISOString();
    const vehicleNumber = vehicleInput?.value.trim() || null;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Booking...';

    try {
        await api.createBooking(selectedSpace.id, startTime, endTime, vehicleNumber);

        hideBookingModal();
        showSuccess('Booking created successfully! View it in My Bookings.');

        // Refresh spaces
        loadSpaces();

    } catch (error) {
        showError(error.message || 'Failed to create booking');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Confirm Booking';
    }
}

/**
 * Format date for datetime-local input
 */
function formatDateTimeLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/**
 * Escape HTML
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
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    } else {
        alert(message);
    }
}

/**
 * Show success message
 */
function showSuccess(message) {
    const successDiv = document.getElementById('success-message');
    if (successDiv) {
        successDiv.textContent = message;
        successDiv.style.display = 'block';
        setTimeout(() => {
            successDiv.style.display = 'none';
        }, 5000);
    } else {
        alert(message);
    }
}
