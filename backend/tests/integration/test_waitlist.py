"""
Integration tests for waitlist routes.
Tests joining, listing, and leaving the waitlist.
"""
import pytest
from datetime import date, time, timedelta


class TestJoinWaitlist:
    """Tests for POST /api/bookings/waitlist"""

    @pytest.mark.integration
    def test_join_waitlist_with_space(self, client, auth_headers, sample_parking_space):
        """Should join waitlist for specific space."""
        tomorrow = date.today() + timedelta(days=1)
        response = client.post(
            '/api/bookings/waitlist',
            headers=auth_headers,
            json={
                'space_id': sample_parking_space['id'],
                'desired_date': tomorrow.isoformat(),
                'start_time': '10:00',
                'end_time': '14:00'
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert 'waitlist_entry' in data
        assert data['waitlist_entry']['space_id'] == sample_parking_space['id']
        assert data['waitlist_entry']['status'] == 'waiting'

    @pytest.mark.integration
    def test_join_waitlist_with_location(self, client, auth_headers):
        """Should join waitlist for location (any space)."""
        tomorrow = date.today() + timedelta(days=1)
        response = client.post(
            '/api/bookings/waitlist',
            headers=auth_headers,
            json={
                'location': 'Mall Parking - Level 1',
                'desired_date': tomorrow.isoformat(),
                'start_time': '09:00',
                'end_time': '12:00',
                'vehicle_type': 'car'
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert 'waitlist_entry' in data
        assert data['waitlist_entry']['location'] == 'Mall Parking - Level 1'

    @pytest.mark.integration
    def test_join_waitlist_missing_date(self, client, auth_headers, sample_parking_space):
        """Should fail without required date."""
        response = client.post(
            '/api/bookings/waitlist',
            headers=auth_headers,
            json={
                'space_id': sample_parking_space['id'],
                'start_time': '10:00',
                'end_time': '14:00'
            }
        )

        assert response.status_code == 400

    @pytest.mark.integration
    def test_join_waitlist_missing_times(self, client, auth_headers, sample_parking_space):
        """Should fail without start/end times."""
        tomorrow = date.today() + timedelta(days=1)
        response = client.post(
            '/api/bookings/waitlist',
            headers=auth_headers,
            json={
                'space_id': sample_parking_space['id'],
                'desired_date': tomorrow.isoformat()
            }
        )

        assert response.status_code == 400

    @pytest.mark.integration
    def test_join_waitlist_past_date(self, client, auth_headers, sample_parking_space):
        """Should fail for past date."""
        yesterday = date.today() - timedelta(days=1)
        response = client.post(
            '/api/bookings/waitlist',
            headers=auth_headers,
            json={
                'space_id': sample_parking_space['id'],
                'desired_date': yesterday.isoformat(),
                'start_time': '10:00',
                'end_time': '14:00'
            }
        )

        assert response.status_code == 400

    @pytest.mark.integration
    def test_join_waitlist_no_auth(self, client, sample_parking_space):
        """Should fail without authentication."""
        tomorrow = date.today() + timedelta(days=1)
        response = client.post(
            '/api/bookings/waitlist',
            json={
                'space_id': sample_parking_space['id'],
                'desired_date': tomorrow.isoformat(),
                'start_time': '10:00',
                'end_time': '14:00'
            }
        )

        assert response.status_code == 401


class TestListWaitlist:
    """Tests for GET /api/bookings/waitlist"""

    @pytest.mark.integration
    def test_list_waitlist_entries(self, client, auth_headers, sample_waitlist_entry):
        """Should list user's waitlist entries."""
        response = client.get(
            '/api/bookings/waitlist',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'waitlist_entries' in data
        assert isinstance(data['waitlist_entries'], list)
        assert len(data['waitlist_entries']) >= 1

    @pytest.mark.integration
    def test_list_waitlist_empty(self, client, auth_headers):
        """Should return empty list when no waitlist entries."""
        response = client.get(
            '/api/bookings/waitlist',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'waitlist_entries' in data
        assert data['waitlist_entries'] == []

    @pytest.mark.integration
    def test_list_waitlist_no_auth(self, client):
        """Should fail without authentication."""
        response = client.get('/api/bookings/waitlist')

        assert response.status_code == 401


class TestLeaveWaitlist:
    """Tests for DELETE /api/bookings/waitlist/<id>"""

    @pytest.mark.integration
    def test_leave_waitlist(self, client, auth_headers, sample_waitlist_entry):
        """Should leave the waitlist."""
        response = client.delete(
            f'/api/bookings/waitlist/{sample_waitlist_entry["id"]}',
            headers=auth_headers
        )

        assert response.status_code == 200
        assert 'removed' in response.get_json()['message'].lower()

    @pytest.mark.integration
    def test_leave_waitlist_not_found(self, client, auth_headers):
        """Should return 404 for non-existent waitlist entry."""
        response = client.delete(
            '/api/bookings/waitlist/99999',
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_leave_waitlist_wrong_user(self, client, app, sample_waitlist_entry):
        """Should deny removing other user's waitlist entry."""
        from app.models import db, User
        from app.utils.auth import hash_password, generate_token

        # Create another user
        with app.app_context():
            other_user = User(
                email='other3@example.com',
                password_hash=hash_password('Password123'),
                name='Other User 3'
            )
            db.session.add(other_user)
            db.session.commit()
            other_token = generate_token(other_user.id)

        response = client.delete(
            f'/api/bookings/waitlist/{sample_waitlist_entry["id"]}',
            headers={'Authorization': f'Bearer {other_token}'}
        )

        assert response.status_code == 403

    @pytest.mark.integration
    def test_leave_waitlist_no_auth(self, client, sample_waitlist_entry):
        """Should fail without authentication."""
        response = client.delete(
            f'/api/bookings/waitlist/{sample_waitlist_entry["id"]}'
        )

        assert response.status_code == 401
