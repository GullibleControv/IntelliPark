"""
Integration tests for the main Flask app.
Tests health checks, error handlers, and app initialization.
"""
import pytest


class TestHealthCheck:
    """Tests for GET /api/health"""

    @pytest.mark.integration
    def test_health_check(self, client):
        """Health check should return healthy status."""
        response = client.get('/api/health')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'IntelliPark API'


class TestErrorHandlers:
    """Tests for error handlers."""

    @pytest.mark.integration
    def test_404_not_found(self, client):
        """Should return 404 for non-existent routes."""
        response = client.get('/api/nonexistent-route')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    @pytest.mark.integration
    def test_405_method_not_allowed(self, client):
        """Should return 405 for wrong HTTP method."""
        # Try DELETE on health check which only allows GET
        response = client.delete('/api/health')

        assert response.status_code == 405
        data = response.get_json()
        assert 'error' in data


class TestAppConfig:
    """Tests for app configuration."""

    @pytest.mark.integration
    def test_testing_mode_enabled(self, app):
        """App should be in testing mode."""
        assert app.config['TESTING'] is True

    @pytest.mark.integration
    def test_database_uri_is_sqlite(self, app):
        """Test database should use SQLite in memory."""
        assert 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']


class TestInitDatabase:
    """Tests for POST /api/init-db"""

    @pytest.mark.integration
    def test_init_db_endpoint(self, client):
        """Should initialize database successfully in test mode (no secret required)."""
        response = client.post(
            '/api/init-db',
            json={},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'successfully' in data['status'].lower()
