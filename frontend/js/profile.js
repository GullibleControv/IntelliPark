/**
 * IntelliPark Profile Page Logic
 */

document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication
    if (!api.isAuthenticated()) {
        window.location.href = 'login.html?return=' + encodeURIComponent(window.location.href);
        return;
    }

    await loadProfile();
    setupEventListeners();
});

/**
 * Load user profile data
 */
async function loadProfile() {
    const profileContainer = document.getElementById('profile-content');

    try {
        const response = await api.getProfile();
        const user = response.user;

        // Update form fields
        document.getElementById('profile-name').value = user.name || '';
        document.getElementById('profile-email').value = user.email || '';
        document.getElementById('profile-phone').value = user.phone || '';

        // Update display name
        const displayName = document.getElementById('display-name');
        if (displayName) {
            displayName.textContent = user.name;
        }

        // Update member since
        const memberSince = document.getElementById('member-since');
        if (memberSince && user.created_at) {
            const date = new Date(user.created_at);
            memberSince.textContent = `Member since ${date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}`;
        }

    } catch (error) {
        showMessage('error-message', error.message || 'Failed to load profile');
    }
}

/**
 * Setup form event listeners
 */
function setupEventListeners() {
    // Profile update form
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', handleProfileUpdate);
    }

    // Password change form
    const passwordForm = document.getElementById('password-form');
    if (passwordForm) {
        passwordForm.addEventListener('submit', handlePasswordChange);
    }
}

/**
 * Handle profile update
 */
async function handleProfileUpdate(e) {
    e.preventDefault();

    const name = document.getElementById('profile-name').value.trim();
    const phone = document.getElementById('profile-phone').value.trim();
    const submitBtn = e.target.querySelector('button[type="submit"]');

    hideMessages();

    if (!name) {
        showMessage('error-message', 'Name is required');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving...';

    try {
        await api.updateProfile({ name, phone: phone || null });
        showMessage('success-message', 'Profile updated successfully!');

        // Update navbar greeting
        auth.updateNavbar();

    } catch (error) {
        showMessage('error-message', error.message || 'Failed to update profile');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Save Changes';
    }
}

/**
 * Handle password change
 */
async function handlePasswordChange(e) {
    e.preventDefault();

    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-new-password').value;
    const submitBtn = e.target.querySelector('button[type="submit"]');

    hideMessages();

    // Validation
    if (!currentPassword || !newPassword || !confirmPassword) {
        showMessage('password-error', 'All fields are required');
        return;
    }

    if (newPassword !== confirmPassword) {
        showMessage('password-error', 'New passwords do not match');
        return;
    }

    if (newPassword.length < 8) {
        showMessage('password-error', 'Password must be at least 8 characters');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Changing...';

    try {
        await api.changePassword(currentPassword, newPassword);
        showMessage('password-success', 'Password changed successfully!');

        // Clear form
        document.getElementById('current-password').value = '';
        document.getElementById('new-password').value = '';
        document.getElementById('confirm-new-password').value = '';

    } catch (error) {
        showMessage('password-error', error.message || 'Failed to change password');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Change Password';
    }
}

/**
 * Show message
 */
function showMessage(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.style.display = 'block';
    }
}

/**
 * Hide all messages
 */
function hideMessages() {
    const messages = ['error-message', 'success-message', 'password-error', 'password-success'];
    messages.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.style.display = 'none';
        }
    });
}

/**
 * Logout function (called from HTML)
 */
function logout() {
    api.logout();
}
