"""
Integration tests for booking routes.
Tests the full request/response cycle for booking endpoints.
"""
import pytest
from datetime import datetime, timedelta

from app.models import db, Booking


class TestCreateBooking:
    """Tests for POST /api/bookings"""

    @pytest.mark.integration
    def test_create_booking_success(self, client, auth_headers, sample_parking_space):
        """Should create a booking successfully."""
        start_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=3)).isoformat()

        response = client.post('/api/bookings', headers=auth_headers, json={
            'space_id': sample_parking_space['id'],
            'start_time': start_time,
            'end_time': end_time,
            'vehicle_number': 'ABC-1234'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['booking']['status'] == 'confirmed'
        assert data['booking']['vehicle_number'] == 'ABC-1234'
        # 2 hours at 50/hour = 100
        assert data['booking']['total_amount'] == 100.0

    @pytest.mark.integration
    def test_create_booking_without_vehicle_number(self, client, auth_headers, sample_parking_space):
        """Should create booking without vehicle number."""
        start_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=2)).isoformat()

        response = client.post('/api/bookings', headers=auth_headers, json={
            'space_id': sample_parking_space['id'],
            'start_time': start_time,
            'end_time': end_time
        })

        assert response.status_code == 201

    @pytest.mark.integration
    def test_create_booking_no_auth(self, client, sample_parking_space):
        """Should fail without authentication."""
        start_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=2)).isoformat()

        response = client.post('/api/bookings', json={
            'space_id': sample_parking_space['id'],
            'start_time': start_time,
            'end_time': end_time
        })

        assert response.status_code == 401

    @pytest.mark.integration
    def test_create_booking_invalid_space(self, client, auth_headers):
        """Should fail with non-existent space."""
        start_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=2)).isoformat()

        response = client.post('/api/bookings', headers=auth_headers, json={
            'space_id': 99999,
            'start_time': start_time,
            'end_time': end_time
        })

        assert response.status_code == 404

    @pytest.mark.integration
    def test_create_booking_past_time(self, client, auth_headers, sample_parking_space):
        """Should fail with past start time."""
        start_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()

        response = client.post('/api/bookings', headers=auth_headers, json={
            'space_id': sample_parking_space['id'],
            'start_time': start_time,
            'end_time': end_time
        })

        assert response.status_code == 400
        assert 'past' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_create_booking_end_before_start(self, client, auth_headers, sample_parking_space):
        """Should fail when end time is before start time."""
        start_time = (datetime.utcnow() + timedelta(hours=3)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()

        response = client.post('/api/bookings', headers=auth_headers, json={
            'space_id': sample_parking_space['id'],
            'start_time': start_time,
            'end_time': end_time
        })

        assert response.status_code == 400
        assert 'after' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_create_booking_conflict(self, client, auth_headers, sample_booking, sample_parking_space):
        """Should fail with conflicting booking."""
        # sample_booking is 1-3 hours from now, try to book overlapping time
        start_time = (datetime.utcnow() + timedelta(hours=2)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=4)).isoformat()

        response = client.post('/api/bookings', headers=auth_headers, json={
            'space_id': sample_parking_space['id'],
            'start_time': start_time,
            'end_time': end_time
        })

        assert response.status_code == 409
        assert 'already booked' in response.get_json()['error'].lower()


class TestGetUserBookings:
    """Tests for GET /api/bookings"""

    @pytest.mark.integration
    def test_get_bookings_success(self, client, auth_headers, sample_booking):
        """Should return user's bookings."""
        response = client.get('/api/bookings', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] >= 1
        assert len(data['bookings']) >= 1

    @pytest.mark.integration
    def test_get_bookings_pagination(self, client, auth_headers, sample_booking):
        """Should support pagination."""
        response = client.get('/api/bookings?page=1&per_page=5', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert 'page' in data
        assert 'per_page' in data
        assert 'pages' in data

    @pytest.mark.integration
    def test_get_bookings_filter_by_status(self, client, auth_headers, sample_booking):
        """Should filter by status."""
        response = client.get('/api/bookings?status=confirmed', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        for booking in data['bookings']:
            assert booking['status'] == 'confirmed'


class TestGetSingleBooking:
    """Tests for GET /api/bookings/<id>"""

    @pytest.mark.integration
    def test_get_booking_success(self, client, auth_headers, sample_booking):
        """Should return booking details."""
        response = client.get(
            f'/api/bookings/{sample_booking["id"]}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['booking']['id'] == sample_booking['id']

    @pytest.mark.integration
    def test_get_booking_not_found(self, client, auth_headers):
        """Should return 404 for non-existent booking."""
        response = client.get('/api/bookings/99999', headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.integration
    def test_get_booking_access_denied(self, client, app, sample_booking):
        """Should deny access to other user's booking."""
        # Create another user and token
        from app.models import User
        from app.utils.auth import hash_password, generate_token

        with app.app_context():
            other_user = User(
                email='other@example.com',
                password_hash=hash_password('Password123'),
                name='Other User'
            )
            db.session.add(other_user)
            db.session.commit()
            other_token = generate_token(other_user.id)

        response = client.get(
            f'/api/bookings/{sample_booking["id"]}',
            headers={'Authorization': f'Bearer {other_token}'}
        )

        assert response.status_code == 403


class TestCancelBooking:
    """Tests for POST /api/bookings/<id>/cancel"""

    @pytest.mark.integration
    def test_cancel_booking_success(self, client, auth_headers, sample_booking):
        """Should cancel a confirmed booking."""
        response = client.post(
            f'/api/bookings/{sample_booking["id"]}/cancel',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['booking']['status'] == 'cancelled'

    @pytest.mark.integration
    def test_cancel_already_cancelled(self, client, app, auth_headers, sample_booking):
        """Should fail to cancel already cancelled booking."""
        # First cancel
        client.post(
            f'/api/bookings/{sample_booking["id"]}/cancel',
            headers=auth_headers
        )

        # Try to cancel again
        response = client.post(
            f'/api/bookings/{sample_booking["id"]}/cancel',
            headers=auth_headers
        )

        assert response.status_code == 400
        assert 'already cancelled' in response.get_json()['error'].lower()


class TestStartBooking:
    """Tests for POST /api/bookings/<id>/start"""

    @pytest.mark.integration
    def test_start_booking_success(self, client, auth_headers, sample_booking):
        """Should mark booking as active."""
        response = client.post(
            f'/api/bookings/{sample_booking["id"]}/start',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['booking']['status'] == 'active'

    @pytest.mark.integration
    def test_start_non_confirmed_booking(self, client, app, auth_headers, sample_booking):
        """Should fail to start non-confirmed booking."""
        # Cancel first
        client.post(
            f'/api/bookings/{sample_booking["id"]}/cancel',
            headers=auth_headers
        )

        # Try to start
        response = client.post(
            f'/api/bookings/{sample_booking["id"]}/start',
            headers=auth_headers
        )

        assert response.status_code == 400


class TestCompleteBooking:
    """Tests for POST /api/bookings/<id>/complete"""

    @pytest.mark.integration
    def test_complete_booking_success(self, client, auth_headers, sample_booking):
        """Should complete an active booking."""
        # First start the booking
        client.post(
            f'/api/bookings/{sample_booking["id"]}/start',
            headers=auth_headers
        )

        # Then complete
        response = client.post(
            f'/api/bookings/{sample_booking["id"]}/complete',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['booking']['status'] == 'completed'

    @pytest.mark.integration
    def test_complete_non_active_booking(self, client, auth_headers, sample_booking):
        """Should fail to complete non-active booking."""
        response = client.post(
            f'/api/bookings/{sample_booking["id"]}/complete',
            headers=auth_headers
        )

        assert response.status_code == 400


class TestActiveBookings:
    """Tests for GET /api/bookings/active"""

    @pytest.mark.integration
    def test_get_active_bookings(self, client, auth_headers, sample_booking):
        """Should return active bookings."""
        # Start the booking first
        client.post(
            f'/api/bookings/{sample_booking["id"]}/start',
            headers=auth_headers
        )

        response = client.get('/api/bookings/active', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] >= 1
        for booking in data['bookings']:
            assert booking['status'] == 'active'


class TestUpcomingBookings:
    """Tests for GET /api/bookings/upcoming"""

    @pytest.mark.integration
    def test_get_upcoming_bookings(self, client, auth_headers, sample_booking):
        """Should return upcoming confirmed bookings."""
        response = client.get('/api/bookings/upcoming', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        # sample_booking is in the future and confirmed
        assert data['count'] >= 1
