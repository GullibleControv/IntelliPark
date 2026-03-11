/**
 * IntelliPark API Client
 * Handles all API communication with the backend
 */

// Use relative URL for Docker (nginx proxy) or absolute for local dev
const API_BASE_URL = window.location.port === '8080' ? '/api' : 'http://localhost:5000/api';

class ApiClient {
    constructor() {
        this.baseUrl = API_BASE_URL;
    }

    /**
     * Get the stored auth token
     */
    getToken() {
        return localStorage.getItem('intellipark_token');
    }

    /**
     * Set the auth token
     */
    setToken(token) {
        localStorage.setItem('intellipark_token', token);
    }

    /**
     * Clear the auth token
     */
    clearToken() {
        localStorage.removeItem('intellipark_token');
        localStorage.removeItem('intellipark_user');
    }

    /**
     * Store user data
     */
    setUser(user) {
        localStorage.setItem('intellipark_user', JSON.stringify(user));
    }

    /**
     * Get stored user data
     */
    getUser() {
        const userData = localStorage.getItem('intellipark_user');
        return userData ? JSON.parse(userData) : null;
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!this.getToken();
    }

    /**
     * Make an API request
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        // Add auth token if available
        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            const data = await response.json();

            if (!response.ok) {
                throw new ApiError(data.error || 'Request failed', response.status);
            }

            return data;
        } catch (error) {
            if (error instanceof ApiError) {
                throw error;
            }
            throw new ApiError('Network error. Please check your connection.', 0);
        }
    }

    // ==================== AUTH ENDPOINTS ====================

    /**
     * Register a new user
     */
    async register(email, password, name, phone = null) {
        const data = await this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password, name, phone })
        });

        this.setToken(data.token);
        this.setUser(data.user);
        return data;
    }

    /**
     * Login user
     */
    async login(email, password) {
        const data = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });

        this.setToken(data.token);
        this.setUser(data.user);
        return data;
    }

    /**
     * Logout user
     */
    logout() {
        this.clearToken();
        window.location.href = '/login.html';
    }

    /**
     * Get current user profile
     */
    async getProfile() {
        return this.request('/auth/me');
    }

    /**
     * Update user profile
     */
    async updateProfile(data) {
        const response = await this.request('/auth/me', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        this.setUser(response.user);
        return response;
    }

    /**
     * Change password
     */
    async changePassword(currentPassword, newPassword) {
        return this.request('/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
    }

    // ==================== PARKING ENDPOINTS ====================

    /**
     * Get all parking spaces
     */
    async getSpaces(filters = {}) {
        const params = new URLSearchParams();
        if (filters.location) params.append('location', filters.location);
        if (filters.available) params.append('available', 'true');
        if (filters.vehicle_type) params.append('vehicle_type', filters.vehicle_type);

        const query = params.toString() ? `?${params.toString()}` : '';
        return this.request(`/parking/spaces${query}`);
    }

    /**
     * Get a single parking space
     */
    async getSpace(spaceId) {
        return this.request(`/parking/spaces/${spaceId}`);
    }

    /**
     * Get parking status summary
     */
    async getParkingStatus(location = null) {
        const query = location ? `?location=${encodeURIComponent(location)}` : '';
        return this.request(`/parking/status${query}`);
    }

    /**
     * Get available locations
     */
    async getLocations() {
        return this.request('/parking/locations');
    }

    /**
     * Create a parking space (admin)
     */
    async createSpace(spaceData) {
        return this.request('/parking/spaces', {
            method: 'POST',
            body: JSON.stringify(spaceData)
        });
    }

    // ==================== BOOKING ENDPOINTS ====================

    /**
     * Create a new booking
     */
    async createBooking(spaceId, startTime, endTime, vehicleNumber = null) {
        return this.request('/bookings', {
            method: 'POST',
            body: JSON.stringify({
                space_id: spaceId,
                start_time: startTime,
                end_time: endTime,
                vehicle_number: vehicleNumber
            })
        });
    }

    /**
     * Get user's bookings
     */
    async getBookings(status = null, page = 1, perPage = 10) {
        const params = new URLSearchParams();
        if (status) params.append('status', status);
        params.append('page', page);
        params.append('per_page', perPage);

        return this.request(`/bookings?${params.toString()}`);
    }

    /**
     * Get a specific booking
     */
    async getBooking(bookingId) {
        return this.request(`/bookings/${bookingId}`);
    }

    /**
     * Cancel a booking
     */
    async cancelBooking(bookingId) {
        return this.request(`/bookings/${bookingId}/cancel`, {
            method: 'POST'
        });
    }

    /**
     * Start a booking (check-in)
     */
    async startBooking(bookingId) {
        return this.request(`/bookings/${bookingId}/start`, {
            method: 'POST'
        });
    }

    /**
     * Complete a booking (check-out)
     */
    async completeBooking(bookingId) {
        return this.request(`/bookings/${bookingId}/complete`, {
            method: 'POST'
        });
    }

    /**
     * Get active bookings
     */
    async getActiveBookings() {
        return this.request('/bookings/active');
    }

    /**
     * Get upcoming bookings
     */
    async getUpcomingBookings() {
        return this.request('/bookings/upcoming');
    }
}

/**
 * Custom API Error class
 */
class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
    }
}

// Create global API instance
const api = new ApiClient();
