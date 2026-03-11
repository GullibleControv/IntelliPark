/**
 * IntelliPark Bookings Page Logic
 */

document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication
    if (!api.isAuthenticated()) {
        window.location.href = 'login.html?return=' + encodeURIComponent(window.location.href);
        return;
    }

    await loadBookings();
    setupFilters();
});

/**
 * Load user bookings
 */
async function loadBookings(status = null) {
    const container = document.getElementById('bookings-list');
    const loadingDiv = document.getElementById('loading');
    const emptyDiv = document.getElementById('empty-state');

    if (loadingDiv) loadingDiv.style.display = 'block';
    if (emptyDiv) emptyDiv.style.display = 'none';
    if (container) container.innerHTML = '';

    try {
        const response = await api.getBookings(status);
        const bookings = response.bookings;

        if (loadingDiv) loadingDiv.style.display = 'none';

        if (bookings.length === 0) {
            if (emptyDiv) emptyDiv.style.display = 'block';
            return;
        }

        bookings.forEach(booking => {
            container.appendChild(createBookingCard(booking));
        });

    } catch (error) {
        if (loadingDiv) loadingDiv.style.display = 'none';
        showError(error.message || 'Failed to load bookings');
    }
}

/**
 * Create a booking card element
 */
function createBookingCard(booking) {
    const card = document.createElement('div');
    card.className = `booking-card status-${booking.status}`;
    card.dataset.bookingId = booking.id;

    const startDate = new Date(booking.start_time);
    const endDate = new Date(booking.end_time);

    card.innerHTML = `
        <div class="booking-header">
            <h3>${escapeHtml(booking.space_name || 'Parking Space')}</h3>
            <span class="booking-status ${booking.status}">${formatStatus(booking.status)}</span>
        </div>
        <div class="booking-details">
            <div class="booking-detail">
                <span class="label">Location</span>
                <span class="value">${escapeHtml(booking.location || 'N/A')}</span>
            </div>
            <div class="booking-detail">
                <span class="label">Date</span>
                <span class="value">${formatDate(startDate)}</span>
            </div>
            <div class="booking-detail">
                <span class="label">Time</span>
                <span class="value">${formatTime(startDate)} - ${formatTime(endDate)}</span>
            </div>
            <div class="booking-detail">
                <span class="label">Amount</span>
                <span class="value">Rs. ${booking.total_amount.toFixed(2)}</span>
            </div>
            ${booking.vehicle_number ? `
            <div class="booking-detail">
                <span class="label">Vehicle</span>
                <span class="value">${escapeHtml(booking.vehicle_number)}</span>
            </div>
            ` : ''}
        </div>
        <div class="booking-actions">
            ${getBookingActions(booking)}
        </div>
    `;

    return card;
}

/**
 * Get available actions for a booking
 */
function getBookingActions(booking) {
    const actions = [];

    if (booking.status === 'confirmed') {
        actions.push(`<button class="btn btn-primary" onclick="startBooking(${booking.id})">Check In</button>`);
        actions.push(`<button class="btn btn-outline" onclick="cancelBooking(${booking.id})">Cancel</button>`);
    } else if (booking.status === 'active') {
        actions.push(`<button class="btn btn-primary" onclick="completeBooking(${booking.id})">Check Out</button>`);
    }

    return actions.join('');
}

/**
 * Setup filter buttons
 */
function setupFilters() {
    const filterBtns = document.querySelectorAll('.filter-btn');

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active state
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Load filtered bookings
            const status = btn.dataset.status || null;
            loadBookings(status);
        });
    });
}

/**
 * Cancel a booking
 */
async function cancelBooking(bookingId) {
    if (!confirm('Are you sure you want to cancel this booking?')) {
        return;
    }

    try {
        await api.cancelBooking(bookingId);
        showSuccess('Booking cancelled successfully');
        loadBookings();
    } catch (error) {
        showError(error.message || 'Failed to cancel booking');
    }
}

/**
 * Start a booking (check in)
 */
async function startBooking(bookingId) {
    try {
        await api.startBooking(bookingId);
        showSuccess('Checked in successfully!');
        loadBookings();
    } catch (error) {
        showError(error.message || 'Failed to check in');
    }
}

/**
 * Complete a booking (check out)
 */
async function completeBooking(bookingId) {
    try {
        await api.completeBooking(bookingId);
        showSuccess('Checked out successfully!');
        loadBookings();
    } catch (error) {
        showError(error.message || 'Failed to check out');
    }
}

/**
 * Format booking status
 */
function formatStatus(status) {
    const statusMap = {
        'pending': 'Pending',
        'confirmed': 'Confirmed',
        'active': 'Active',
        'completed': 'Completed',
        'cancelled': 'Cancelled'
    };
    return statusMap[status] || status;
}

/**
 * Format date
 */
function formatDate(date) {
    return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

/**
 * Format time
 */
function formatTime(date) {
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
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
    }
}
