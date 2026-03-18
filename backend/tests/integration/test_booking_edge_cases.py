"""
Integration tests for booking routes edge cases.
Tests error handling and edge scenarios.
"""
import pytest
from datetime import datetime, timedelta


class TestBookingEdgeCases:
    """Tests for booking edge cases."""

    @pytest.mark.integration
    def test_create_booking_with_valid_data(self, client, auth_headers, sample_parking_space):
        """Should create booking with valid data."""
        start_time = datetime.utcnow() + timedelta(hours=2)
        end_time = start_time + timedelta(hours=3)

        response = client.post(
            '/api/bookings',
            headers=auth_headers,
            json={
                'space_id': sample_parking_space['id'],
                'start_time': start_time.isoformat(),  # Without 'Z' to match naive datetime comparison
                'end_time': end_time.isoformat()
            }
        )

        assert response.status_code == 201

    @pytest.mark.integration
    def test_cancel_completed_booking(self, client, auth_headers, sample_booking, app):
        """Should not allow cancelling completed booking."""
        from app.models import db, Booking

        with app.app_context():
            booking = Booking.query.get(sample_booking['id'])
            booking.status = 'completed'
            db.session.commit()

        response = client.post(
            f'/api/bookings/{sample_booking["id"]}/cancel',
            headers=auth_headers
        )

        assert response.status_code == 400
        assert 'completed' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_cancel_active_booking(self, client, auth_headers, sample_booking, app):
        """Should not allow cancelling active booking."""
        from app.models import db, Booking

        with app.app_context():
            booking = Booking.query.get(sample_booking['id'])
            booking.status = 'active'
            db.session.commit()

        response = client.post(
            f'/api/bookings/{sample_booking["id"]}/cancel',
            headers=auth_headers
        )

        assert response.status_code == 400
        assert 'active' in response.get_json()['error'].lower()


class TestRecurringBookingEdgeCases:
    """Tests for recurring booking edge cases."""

    @pytest.mark.integration
    def test_create_recurring_end_before_start(self, client, auth_headers, sample_parking_space):
        """Should reject recurring booking with end before start."""
        from datetime import date

        response = client.post(
            '/api/bookings/recurring',
            headers=auth_headers,
            json={
                'space_id': sample_parking_space['id'],
                'pattern': 'weekdays',
                'start_time': '17:00',
                'end_time': '09:00',  # End before start
                'valid_from': date.today().isoformat()
            }
        )

        assert response.status_code == 400
        assert 'end time' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_create_recurring_with_invalid_time_format(self, client, auth_headers, sample_parking_space):
        """Should reject recurring booking with invalid time format."""
        from datetime import date

        response = client.post(
            '/api/bookings/recurring',
            headers=auth_headers,
            json={
                'space_id': sample_parking_space['id'],
                'pattern': 'weekdays',
                'start_time': 'invalid',
                'end_time': 'also_invalid',
                'valid_from': date.today().isoformat()
            }
        )

        assert response.status_code == 400


class TestWaitlistEdgeCases:
    """Tests for waitlist edge cases."""

    @pytest.mark.integration
    def test_join_waitlist_end_before_start(self, client, auth_headers, sample_parking_space):
        """Should reject waitlist entry with end before start."""
        from datetime import date, timedelta

        tomorrow = date.today() + timedelta(days=1)
        response = client.post(
            '/api/bookings/waitlist',
            headers=auth_headers,
            json={
                'space_id': sample_parking_space['id'],
                'desired_date': tomorrow.isoformat(),
                'start_time': '14:00',
                'end_time': '10:00'  # End before start
            }
        )

        assert response.status_code == 400
        assert 'end time' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_join_waitlist_no_space_or_location(self, client, auth_headers):
        """Should reject waitlist entry without space or location."""
        from datetime import date, timedelta

        tomorrow = date.today() + timedelta(days=1)
        response = client.post(
            '/api/bookings/waitlist',
            headers=auth_headers,
            json={
                'desired_date': tomorrow.isoformat(),
                'start_time': '10:00',
                'end_time': '14:00'
                # Missing both space_id and location
            }
        )

        assert response.status_code == 400

    @pytest.mark.integration
    def test_join_waitlist_duplicate(self, client, auth_headers, sample_waitlist_entry, app):
        """Should reject duplicate waitlist entry for same date."""
        from datetime import date, timedelta

        tomorrow = date.today() + timedelta(days=1)
        response = client.post(
            '/api/bookings/waitlist',
            headers=auth_headers,
            json={
                'space_id': sample_waitlist_entry['space_id'],
                'desired_date': tomorrow.isoformat(),
                'start_time': '10:00',
                'end_time': '12:00'
            }
        )

        assert response.status_code == 409
        assert 'already' in response.get_json()['error'].lower()
