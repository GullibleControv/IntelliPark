"""
Integration tests for error handling and edge cases.
Tests exception handling paths in routes.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestAuthErrorHandling:
    """Tests for error handling in auth routes."""

    @pytest.mark.integration
    def test_register_empty_object(self, client):
        """Should handle empty object request body."""
        response = client.post('/api/auth/register', json={})
        assert response.status_code == 400

    @pytest.mark.integration
    def test_login_empty_object(self, client):
        """Should handle empty object request body."""
        response = client.post('/api/auth/login', json={})
        assert response.status_code == 400

    @pytest.mark.integration
    def test_change_password_missing_fields(self, client, auth_headers):
        """Should fail with missing password fields."""
        response = client.post('/api/auth/change-password',
                               headers=auth_headers,
                               json={'current_password': 'TestPass123'})
        assert response.status_code == 400


class TestParkingErrorHandling:
    """Tests for error handling in parking routes."""

    @pytest.mark.integration
    def test_create_space_missing_name(self, client, admin_headers):
        """Should fail with missing name (admin only)."""
        response = client.post('/api/parking/spaces',
                               headers=admin_headers,
                               json={'location': 'Test'})
        assert response.status_code == 400

    @pytest.mark.integration
    def test_create_space_missing_location(self, client, admin_headers):
        """Should fail with missing location (admin only)."""
        response = client.post('/api/parking/spaces',
                               headers=admin_headers,
                               json={'name': 'A-001'})
        assert response.status_code == 400

    @pytest.mark.integration
    def test_update_status_missing_is_occupied(self, client, sample_parking_space):
        """Should fail without is_occupied field."""
        response = client.put(f'/api/parking/spaces/{sample_parking_space["id"]}/status',
                              json={'confidence': 0.9})
        assert response.status_code == 400


class TestBookingErrorHandling:
    """Tests for error handling in booking routes."""

    @pytest.mark.integration
    def test_create_booking_missing_space_id(self, client, auth_headers):
        """Should fail with missing space_id."""
        response = client.post('/api/bookings',
                               headers=auth_headers,
                               json={'start_time': '2030-01-01T10:00:00', 'end_time': '2030-01-01T12:00:00'})
        assert response.status_code == 400

    @pytest.mark.integration
    def test_create_booking_invalid_datetime(self, client, auth_headers, sample_parking_space):
        """Should handle invalid datetime format."""
        response = client.post('/api/bookings', headers=auth_headers, json={
            'space_id': sample_parking_space['id'],
            'start_time': 'not-a-date',
            'end_time': 'also-not-a-date'
        })

        assert response.status_code == 400
        assert 'datetime' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_create_booking_inactive_space(self, client, app, auth_headers):
        """Should fail when booking inactive space."""
        from app.models import db, ParkingSpace

        with app.app_context():
            space = ParkingSpace(
                name='Inactive',
                location='Test',
                is_active=False
            )
            db.session.add(space)
            db.session.commit()
            space_id = space.id

        start_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=2)).isoformat()

        response = client.post('/api/bookings', headers=auth_headers, json={
            'space_id': space_id,
            'start_time': start_time,
            'end_time': end_time
        })

        assert response.status_code == 400
        assert 'not available' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_create_booking_invalid_vehicle_number(self, client, auth_headers, sample_parking_space):
        """Should fail with invalid vehicle number format."""
        start_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=2)).isoformat()

        response = client.post('/api/bookings', headers=auth_headers, json={
            'space_id': sample_parking_space['id'],
            'start_time': start_time,
            'end_time': end_time,
            'vehicle_number': '@@@INVALID@@@'
        })

        assert response.status_code == 400
        assert 'vehicle' in response.get_json()['error'].lower()


class TestAdminErrorHandling:
    """Tests for error handling in admin routes."""

    @pytest.mark.integration
    def test_video_sources_no_auth(self, client):
        """Should fail without authentication."""
        response = client.get('/api/admin/video-sources')

        assert response.status_code == 401

    @pytest.mark.integration
    def test_spaces_with_coordinates_no_auth(self, client):
        """Should fail without authentication."""
        response = client.get('/api/admin/spaces-with-coordinates')

        assert response.status_code == 401

    @pytest.mark.integration
    def test_bulk_spaces_no_auth(self, client):
        """Should fail without authentication."""
        response = client.post('/api/admin/spaces/bulk', json={
            'spaces': []
        })

        assert response.status_code == 401

    @pytest.mark.integration
    def test_delete_video_source_not_found(self, client, admin_headers):
        """Should return 404 for non-existent source."""
        response = client.delete(
            '/api/admin/video-sources/99999',
            headers=admin_headers
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_detection_config_source_not_found(self, client, admin_headers):
        """Should return 404 for non-existent source."""
        response = client.get(
            '/api/admin/detection/config?source_id=99999',
            headers=admin_headers
        )

        assert response.status_code == 404
