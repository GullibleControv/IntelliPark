"""
Integration tests for recurring booking routes.
Tests creating, listing, and cancelling recurring bookings.
"""
import pytest
from datetime import date, time, timedelta


class TestCreateRecurringBooking:
    """Tests for POST /api/bookings/recurring"""

    @pytest.mark.integration
    def test_create_recurring_booking_success(self, client, auth_headers, sample_parking_space):
        """Should create a recurring booking successfully."""
        response = client.post(
            '/api/bookings/recurring',
            headers=auth_headers,
            json={
                'space_id': sample_parking_space['id'],
                'pattern': 'weekdays',
                'start_time': '09:00',
                'end_time': '17:00',
                'valid_from': date.today().isoformat(),
                'vehicle_number': 'ABC-1234'
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert 'recurring_booking' in data
        assert data['recurring_booking']['pattern'] == 'weekdays'
        assert data['recurring_booking']['space_id'] == sample_parking_space['id']

    @pytest.mark.integration
    def test_create_recurring_booking_with_days(self, client, auth_headers, sample_parking_space):
        """Should create weekly recurring booking with specific days."""
        response = client.post(
            '/api/bookings/recurring',
            headers=auth_headers,
            json={
                'space_id': sample_parking_space['id'],
                'pattern': 'weekly',
                'start_time': '08:00',
                'end_time': '12:00',
                'valid_from': date.today().isoformat(),
                'valid_until': (date.today() + timedelta(days=90)).isoformat(),
                'days_of_week': [0, 2, 4]  # Mon, Wed, Fri
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert 'recurring_booking' in data
        assert data['recurring_booking']['pattern'] == 'weekly'
        assert data['recurring_booking']['days_of_week'] == [0, 2, 4]

    @pytest.mark.integration
    def test_create_recurring_missing_required(self, client, auth_headers):
        """Should fail without required fields."""
        response = client.post(
            '/api/bookings/recurring',
            headers=auth_headers,
            json={}
        )

        assert response.status_code == 400

    @pytest.mark.integration
    def test_create_recurring_invalid_pattern(self, client, auth_headers, sample_parking_space):
        """Should fail with invalid pattern."""
        response = client.post(
            '/api/bookings/recurring',
            headers=auth_headers,
            json={
                'space_id': sample_parking_space['id'],
                'pattern': 'invalid_pattern',
                'start_time': '09:00',
                'end_time': '17:00',
                'valid_from': date.today().isoformat()
            }
        )

        assert response.status_code == 400
        assert 'pattern' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_create_recurring_invalid_space(self, client, auth_headers):
        """Should fail with non-existent space."""
        response = client.post(
            '/api/bookings/recurring',
            headers=auth_headers,
            json={
                'space_id': 99999,
                'pattern': 'daily',
                'start_time': '09:00',
                'end_time': '17:00',
                'valid_from': date.today().isoformat()
            }
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_create_recurring_no_auth(self, client, sample_parking_space):
        """Should fail without authentication."""
        response = client.post(
            '/api/bookings/recurring',
            json={
                'space_id': sample_parking_space['id'],
                'pattern': 'daily',
                'start_time': '09:00',
                'end_time': '17:00',
                'valid_from': date.today().isoformat()
            }
        )

        assert response.status_code == 401


class TestListRecurringBookings:
    """Tests for GET /api/bookings/recurring"""

    @pytest.mark.integration
    def test_list_recurring_bookings(self, client, auth_headers, sample_recurring_booking):
        """Should list user's recurring bookings."""
        response = client.get(
            '/api/bookings/recurring',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'recurring_bookings' in data
        assert isinstance(data['recurring_bookings'], list)
        assert len(data['recurring_bookings']) >= 1

    @pytest.mark.integration
    def test_list_recurring_bookings_empty(self, client, auth_headers):
        """Should return empty list when no recurring bookings."""
        response = client.get(
            '/api/bookings/recurring',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'recurring_bookings' in data
        assert data['recurring_bookings'] == []

    @pytest.mark.integration
    def test_list_recurring_no_auth(self, client):
        """Should fail without authentication."""
        response = client.get('/api/bookings/recurring')

        assert response.status_code == 401


class TestCancelRecurringBooking:
    """Tests for DELETE /api/bookings/recurring/<id>"""

    @pytest.mark.integration
    def test_cancel_recurring_booking(self, client, auth_headers, sample_recurring_booking):
        """Should cancel a recurring booking."""
        response = client.delete(
            f'/api/bookings/recurring/{sample_recurring_booking["id"]}',
            headers=auth_headers
        )

        assert response.status_code == 200
        assert 'cancelled' in response.get_json()['message'].lower()

    @pytest.mark.integration
    def test_cancel_recurring_not_found(self, client, auth_headers):
        """Should return 404 for non-existent recurring booking."""
        response = client.delete(
            '/api/bookings/recurring/99999',
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_cancel_recurring_wrong_user(self, client, app, sample_recurring_booking):
        """Should deny cancelling other user's recurring booking."""
        from app.models import db, User
        from app.utils.auth import hash_password, generate_token

        # Create another user
        with app.app_context():
            other_user = User(
                email='other2@example.com',
                password_hash=hash_password('Password123'),
                name='Other User 2'
            )
            db.session.add(other_user)
            db.session.commit()
            other_token = generate_token(other_user.id)

        response = client.delete(
            f'/api/bookings/recurring/{sample_recurring_booking["id"]}',
            headers={'Authorization': f'Bearer {other_token}'}
        )

        assert response.status_code == 403

    @pytest.mark.integration
    def test_cancel_recurring_no_auth(self, client, sample_recurring_booking):
        """Should fail without authentication."""
        response = client.delete(
            f'/api/bookings/recurring/{sample_recurring_booking["id"]}'
        )

        assert response.status_code == 401
