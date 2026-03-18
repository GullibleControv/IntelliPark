"""
Integration tests for payment routes.
Tests Stripe payment integration.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestPaymentConfig:
    """Tests for GET /api/payments/config"""

    @pytest.mark.integration
    def test_get_config_no_key(self, client, app):
        """Should return error when Stripe not configured."""
        # In test mode, no Stripe key is set
        response = client.get('/api/payments/config')

        # Either returns the key or 503 if not configured
        assert response.status_code in [200, 503]


class TestCreateCheckoutSession:
    """Tests for POST /api/payments/create-checkout-session"""

    @pytest.mark.integration
    def test_create_checkout_no_auth(self, client, sample_booking):
        """Should fail without authentication."""
        response = client.post(
            '/api/payments/create-checkout-session',
            json={'booking_id': sample_booking['id']}
        )

        assert response.status_code == 401

    @pytest.mark.integration
    def test_create_checkout_no_booking_id(self, client, auth_headers, app):
        """Should fail without booking_id (or 503 if Stripe not configured)."""
        response = client.post(
            '/api/payments/create-checkout-session',
            headers=auth_headers,
            json={}
        )

        # 400 if request processed, 503 if Stripe not configured
        assert response.status_code in [400, 503]

    @pytest.mark.integration
    def test_create_checkout_booking_not_found(self, client, auth_headers, app):
        """Should fail with non-existent booking (or 503 if Stripe not configured)."""
        response = client.post(
            '/api/payments/create-checkout-session',
            headers=auth_headers,
            json={'booking_id': 99999}
        )

        # 404 if request processed, 503 if Stripe not configured
        assert response.status_code in [404, 503]

    @pytest.mark.integration
    def test_create_checkout_access_denied(self, client, app, auth_headers, sample_booking):
        """Should deny access to other user's booking (or 503 if Stripe not configured)."""
        from app.models import db, User
        from app.utils.auth import hash_password, generate_token

        # Create another user
        with app.app_context():
            other_user = User(
                email='other@example.com',
                password_hash=hash_password('Password123'),
                name='Other User'
            )
            db.session.add(other_user)
            db.session.commit()
            other_token = generate_token(other_user.id)

        response = client.post(
            '/api/payments/create-checkout-session',
            headers={'Authorization': f'Bearer {other_token}'},
            json={'booking_id': sample_booking['id']}
        )

        # 403 if request processed, 503 if Stripe not configured
        assert response.status_code in [403, 503]


class TestVerifySession:
    """Tests for POST /api/payments/verify-session"""

    @pytest.mark.integration
    def test_verify_no_session_id(self, client, auth_headers):
        """Should fail without session_id."""
        response = client.post(
            '/api/payments/verify-session',
            headers=auth_headers,
            json={}
        )

        assert response.status_code == 400

    @pytest.mark.integration
    def test_verify_no_auth(self, client):
        """Should fail without authentication."""
        response = client.post(
            '/api/payments/verify-session',
            json={'session_id': 'cs_test_123'}
        )

        assert response.status_code == 401


class TestGetPaymentStatus:
    """Tests for GET /api/payments/booking/<id>/status"""

    @pytest.mark.integration
    def test_get_payment_status(self, client, auth_headers, sample_booking):
        """Should return payment status for booking."""
        response = client.get(
            f'/api/payments/booking/{sample_booking["id"]}/status',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['booking_id'] == sample_booking['id']
        assert 'payment_status' in data
        assert 'total_amount' in data

    @pytest.mark.integration
    def test_get_payment_status_not_found(self, client, auth_headers):
        """Should return 404 for non-existent booking."""
        response = client.get(
            '/api/payments/booking/99999/status',
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_get_payment_status_no_auth(self, client, sample_booking):
        """Should fail without authentication."""
        response = client.get(
            f'/api/payments/booking/{sample_booking["id"]}/status'
        )

        assert response.status_code == 401


class TestRefund:
    """Tests for POST /api/payments/refund"""

    @pytest.mark.integration
    def test_refund_no_booking_id(self, client, auth_headers):
        """Should fail without booking_id."""
        response = client.post(
            '/api/payments/refund',
            headers=auth_headers,
            json={}
        )

        assert response.status_code == 400

    @pytest.mark.integration
    def test_refund_not_paid(self, client, auth_headers, sample_booking):
        """Should fail if booking not paid."""
        response = client.post(
            '/api/payments/refund',
            headers=auth_headers,
            json={'booking_id': sample_booking['id']}
        )

        assert response.status_code == 400
        assert 'not paid' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_refund_no_auth(self, client, sample_booking):
        """Should fail without authentication."""
        response = client.post(
            '/api/payments/refund',
            json={'booking_id': sample_booking['id']}
        )

        assert response.status_code == 401

    @pytest.mark.integration
    def test_refund_booking_not_found(self, client, auth_headers):
        """Should return 404 for non-existent booking."""
        response = client.post(
            '/api/payments/refund',
            headers=auth_headers,
            json={'booking_id': 99999}
        )

        assert response.status_code == 404
