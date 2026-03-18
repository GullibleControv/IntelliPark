"""
Unit tests for authentication decorators.
Tests token_required, optional_token, and admin_required decorators.
"""
import pytest
from flask import Flask, jsonify

from app.models import db, User
from app.utils.auth import (
    token_required,
    optional_token,
    admin_required,
    hash_password,
    generate_token
)


class TestTokenRequiredDecorator:
    """Tests for token_required decorator."""

    @pytest.mark.unit
    def test_valid_token(self, client, auth_headers):
        """Should allow access with valid token."""
        response = client.get('/api/auth/me', headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.unit
    def test_missing_token(self, client):
        """Should reject without token."""
        response = client.get('/api/auth/me')
        assert response.status_code == 401
        assert 'authorization' in response.get_json()['error'].lower()

    @pytest.mark.unit
    def test_invalid_token(self, client):
        """Should reject invalid token."""
        response = client.get('/api/auth/me', headers={
            'Authorization': 'Bearer invalid-token'
        })
        assert response.status_code == 401

    @pytest.mark.unit
    def test_malformed_header(self, client):
        """Should reject malformed Authorization header."""
        response = client.get('/api/auth/me', headers={
            'Authorization': 'NotBearer token'
        })
        assert response.status_code == 401


class TestOptionalTokenDecorator:
    """Tests for optional_token decorator."""

    @pytest.mark.unit
    def test_with_valid_token(self, client, auth_headers):
        """Should extract user_id with valid token."""
        # GET /api/parking/spaces uses optional_token implicitly
        # We test by checking it works with and without token
        response = client.get('/api/parking/spaces', headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.unit
    def test_without_token(self, client):
        """Should work without token."""
        response = client.get('/api/parking/spaces')
        assert response.status_code == 200


class TestAdminRequiredDecorator:
    """Tests for admin_required decorator."""

    @pytest.mark.unit
    def test_admin_access_granted(self, app, client, admin_headers):
        """Should allow admin access."""
        # We need a route that uses admin_required
        # Let's test via a custom route in the app context
        @app.route('/test-admin')
        @admin_required
        def test_admin_route():
            return jsonify({'message': 'Admin access granted'})

        response = client.get('/test-admin', headers=admin_headers)
        assert response.status_code == 200
        assert response.get_json()['message'] == 'Admin access granted'

    @pytest.mark.unit
    def test_non_admin_access_denied(self, app, client, auth_headers):
        """Should deny non-admin access."""
        @app.route('/test-admin-deny')
        @admin_required
        def test_admin_deny_route():
            return jsonify({'message': 'Should not reach here'})

        response = client.get('/test-admin-deny', headers=auth_headers)
        assert response.status_code == 403
        assert 'admin' in response.get_json()['error'].lower()

    @pytest.mark.unit
    def test_no_token_denied(self, app, client):
        """Should deny access without token."""
        @app.route('/test-admin-no-token')
        @admin_required
        def test_admin_no_token_route():
            return jsonify({'message': 'Should not reach here'})

        response = client.get('/test-admin-no-token')
        assert response.status_code == 401

    @pytest.mark.unit
    def test_invalid_token_denied(self, app, client):
        """Should deny access with invalid token."""
        @app.route('/test-admin-invalid')
        @admin_required
        def test_admin_invalid_route():
            return jsonify({'message': 'Should not reach here'})

        response = client.get('/test-admin-invalid', headers={
            'Authorization': 'Bearer invalid-token'
        })
        assert response.status_code == 401
