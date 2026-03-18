"""
Integration tests for authentication routes.
Tests the full request/response cycle for auth endpoints.
"""
import pytest
import json

from app.models import db, User
from app.utils.auth import hash_password


class TestRegister:
    """Tests for POST /api/auth/register"""

    @pytest.mark.integration
    def test_register_success(self, client):
        """Should register a new user successfully."""
        response = client.post('/api/auth/register', json={
            'email': 'newuser@example.com',
            'password': 'ValidPass123',
            'name': 'New User'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert 'token' in data
        assert data['user']['email'] == 'newuser@example.com'
        assert data['user']['name'] == 'New User'
        assert data['user']['is_admin'] is False

    @pytest.mark.integration
    def test_register_with_phone(self, client):
        """Should register with optional phone number."""
        response = client.post('/api/auth/register', json={
            'email': 'withphone@example.com',
            'password': 'ValidPass123',
            'name': 'Phone User',
            'phone': '+1234567890'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['user']['phone'] == '+1234567890'

    @pytest.mark.integration
    def test_register_missing_fields(self, client):
        """Should fail with missing required fields."""
        response = client.post('/api/auth/register', json={
            'email': 'test@example.com'
        })

        assert response.status_code == 400
        assert 'required' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_register_invalid_email(self, client):
        """Should fail with invalid email format."""
        response = client.post('/api/auth/register', json={
            'email': 'invalid-email',
            'password': 'ValidPass123',
            'name': 'Test User'
        })

        assert response.status_code == 400
        assert 'email' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_register_weak_password(self, client):
        """Should fail with weak password."""
        response = client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'password': 'weak',
            'name': 'Test User'
        })

        assert response.status_code == 400
        assert 'password' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_register_duplicate_email(self, client, sample_user):
        """Should fail when email already exists."""
        response = client.post('/api/auth/register', json={
            'email': 'test@example.com',  # Same as sample_user
            'password': 'ValidPass123',
            'name': 'Duplicate User'
        })

        assert response.status_code == 409
        assert 'already registered' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_register_invalid_phone(self, client):
        """Should fail with invalid phone format."""
        response = client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'password': 'ValidPass123',
            'name': 'Test User',
            'phone': 'invalid'
        })

        assert response.status_code == 400
        assert 'phone' in response.get_json()['error'].lower()


class TestLogin:
    """Tests for POST /api/auth/login"""

    @pytest.mark.integration
    def test_login_success(self, client, sample_user):
        """Should login with valid credentials."""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'TestPass123'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'token' in data
        assert data['user']['email'] == 'test@example.com'

    @pytest.mark.integration
    def test_login_wrong_password(self, client, sample_user):
        """Should fail with wrong password."""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'WrongPassword123'
        })

        assert response.status_code == 401
        assert 'invalid' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_login_nonexistent_user(self, client):
        """Should fail with non-existent email."""
        response = client.post('/api/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'SomePassword123'
        })

        assert response.status_code == 401

    @pytest.mark.integration
    def test_login_missing_fields(self, client):
        """Should fail with missing fields."""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com'
        })

        assert response.status_code == 400

    @pytest.mark.integration
    def test_login_case_insensitive_email(self, client, sample_user):
        """Email should be case insensitive."""
        response = client.post('/api/auth/login', json={
            'email': 'TEST@EXAMPLE.COM',
            'password': 'TestPass123'
        })

        assert response.status_code == 200


class TestGetCurrentUser:
    """Tests for GET /api/auth/me"""

    @pytest.mark.integration
    def test_get_current_user_success(self, client, auth_headers):
        """Should return current user profile."""
        response = client.get('/api/auth/me', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert 'user' in data
        assert data['user']['email'] == 'test@example.com'

    @pytest.mark.integration
    def test_get_current_user_no_token(self, client):
        """Should fail without auth token."""
        response = client.get('/api/auth/me')

        assert response.status_code == 401

    @pytest.mark.integration
    def test_get_current_user_invalid_token(self, client):
        """Should fail with invalid token."""
        response = client.get('/api/auth/me', headers={
            'Authorization': 'Bearer invalid-token'
        })

        assert response.status_code == 401


class TestUpdateCurrentUser:
    """Tests for PUT /api/auth/me"""

    @pytest.mark.integration
    def test_update_name(self, client, auth_headers):
        """Should update user name."""
        response = client.put('/api/auth/me', headers=auth_headers, json={
            'name': 'Updated Name'
        })

        assert response.status_code == 200
        assert response.get_json()['user']['name'] == 'Updated Name'

    @pytest.mark.integration
    def test_update_phone(self, client, auth_headers):
        """Should update user phone."""
        response = client.put('/api/auth/me', headers=auth_headers, json={
            'phone': '+9876543210'
        })

        assert response.status_code == 200
        assert response.get_json()['user']['phone'] == '+9876543210'

    @pytest.mark.integration
    def test_update_invalid_phone(self, client, auth_headers):
        """Should fail with invalid phone."""
        response = client.put('/api/auth/me', headers=auth_headers, json={
            'phone': 'invalid'
        })

        assert response.status_code == 400


class TestChangePassword:
    """Tests for POST /api/auth/change-password"""

    @pytest.mark.integration
    def test_change_password_success(self, client, auth_headers):
        """Should change password with valid credentials."""
        response = client.post('/api/auth/change-password', headers=auth_headers, json={
            'current_password': 'TestPass123',
            'new_password': 'NewValidPass456'
        })

        assert response.status_code == 200
        assert 'successfully' in response.get_json()['message'].lower()

    @pytest.mark.integration
    def test_change_password_wrong_current(self, client, auth_headers):
        """Should fail with wrong current password."""
        response = client.post('/api/auth/change-password', headers=auth_headers, json={
            'current_password': 'WrongPassword123',
            'new_password': 'NewValidPass456'
        })

        assert response.status_code == 401
        assert 'incorrect' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_change_password_weak_new(self, client, auth_headers):
        """Should fail with weak new password."""
        response = client.post('/api/auth/change-password', headers=auth_headers, json={
            'current_password': 'TestPass123',
            'new_password': 'weak'
        })

        assert response.status_code == 400
