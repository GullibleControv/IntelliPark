/**
 * IntelliPark Auth Management
 * Handles authentication state and UI updates
 */

class AuthManager {
    constructor() {
        this.init();
    }

    /**
     * Initialize auth state on page load
     */
    init() {
        this.updateNavbar();
        this.checkProtectedPage();
    }

    /**
     * Check if current page requires authentication
     */
    checkProtectedPage() {
        const protectedPages = ['profile.html', 'bookings.html', 'admin.html'];
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';

        if (protectedPages.includes(currentPage) && !api.isAuthenticated()) {
            // Redirect to login with return URL
            const returnUrl = encodeURIComponent(window.location.href);
            window.location.href = `/login.html?return=${returnUrl}`;
        }
    }

    /**
     * Update navbar based on auth state
     */
    updateNavbar() {
        const authNav = document.getElementById('auth-nav');
        if (!authNav) return;

        if (api.isAuthenticated()) {
            const user = api.getUser();
            authNav.innerHTML = `
                <div class="nav-user">
                    <span class="user-greeting">Hello, ${this.escapeHtml(user?.name || 'User')}</span>
                    <a href="/profile.html" class="nav-link">Profile</a>
                    <a href="/bookings.html" class="nav-link">My Bookings</a>
                    <button onclick="auth.logout()" class="btn btn-outline logout-btn">Logout</button>
                </div>
            `;
        } else {
            authNav.innerHTML = `
                <div class="nav-auth">
                    <a href="/login.html" class="btn btn-outline">Login</a>
                    <a href="/register.html" class="btn btn-primary">Register</a>
                </div>
            `;
        }
    }

    /**
     * Handle logout
     */
    logout() {
        api.logout();
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Show error message
     */
    showError(elementId, message) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = message;
            element.style.display = 'block';
            element.classList.add('error-message');
        }
    }

    /**
     * Hide error message
     */
    hideError(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = 'none';
        }
    }

    /**
     * Show success message
     */
    showSuccess(elementId, message) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = message;
            element.style.display = 'block';
            element.classList.add('success-message');
        }
    }

    /**
     * Show loading state on button
     */
    setLoading(button, loading) {
        if (loading) {
            button.disabled = true;
            button.dataset.originalText = button.textContent;
            button.textContent = 'Loading...';
        } else {
            button.disabled = false;
            button.textContent = button.dataset.originalText || button.textContent;
        }
    }

    /**
     * Get URL parameter
     */
    getUrlParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    }

    /**
     * Redirect after login
     */
    redirectAfterLogin() {
        const returnUrl = this.getUrlParam('return');
        if (returnUrl) {
            window.location.href = decodeURIComponent(returnUrl);
        } else {
            window.location.href = '/index.html';
        }
    }
}

// Create global auth manager instance
const auth = new AuthManager();
