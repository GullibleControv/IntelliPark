"""
Integration tests for payment routes with mocked Stripe.
Tests full payment flow with Stripe mocked.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestCreateCheckoutSessionMocked:
    """Tests for create checkout session with mocked Stripe."""

    @pytest.mark.integration
    def test_create_checkout_success(self, client, auth_headers, sample_booking, app):
        """Should create checkout session successfully with mocked Stripe."""
        with app.app_context():
            # Configure Stripe key
            app.config['STRIPE_SECRET_KEY'] = 'sk_test_mock'

            # Mock Stripe checkout session
            mock_session = MagicMock()
            mock_session.id = 'cs_test_123'
            mock_session.url = 'https://checkout.stripe.com/test'

            with patch('stripe.checkout.Session.create', return_value=mock_session):
                response = client.post(
                    '/api/payments/create-checkout-session',
                    headers=auth_headers,
                    json={'booking_id': sample_booking['id']}
                )

                assert response.status_code == 200
                data = response.get_json()
                assert data['session_id'] == 'cs_test_123'
                assert 'url' in data

    @pytest.mark.integration
    def test_create_checkout_already_paid(self, client, auth_headers, sample_booking, app):
        """Should reject checkout for already paid booking."""
        from app.models import db, Booking

        with app.app_context():
            app.config['STRIPE_SECRET_KEY'] = 'sk_test_mock'

            # Mark booking as paid
            booking = Booking.query.get(sample_booking['id'])
            booking.payment_status = 'paid'
            db.session.commit()

            response = client.post(
                '/api/payments/create-checkout-session',
                headers=auth_headers,
                json={'booking_id': sample_booking['id']}
            )

            assert response.status_code == 400
            assert 'already paid' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_create_checkout_cancelled_booking(self, client, auth_headers, sample_booking, app):
        """Should reject checkout for cancelled booking."""
        from app.models import db, Booking

        with app.app_context():
            app.config['STRIPE_SECRET_KEY'] = 'sk_test_mock'

            # Mark booking as cancelled
            booking = Booking.query.get(sample_booking['id'])
            booking.status = 'cancelled'
            db.session.commit()

            response = client.post(
                '/api/payments/create-checkout-session',
                headers=auth_headers,
                json={'booking_id': sample_booking['id']}
            )

            assert response.status_code == 400
            assert 'cancelled' in response.get_json()['error'].lower()


class TestVerifySessionMocked:
    """Tests for verify session with mocked Stripe."""

    @pytest.mark.integration
    def test_verify_session_success(self, client, auth_headers, sample_booking, app):
        """Should verify payment session successfully."""
        with app.app_context():
            app.config['STRIPE_SECRET_KEY'] = 'sk_test_mock'

            mock_session = MagicMock()
            mock_session.payment_status = 'paid'
            mock_session.metadata = {'booking_id': str(sample_booking['id'])}
            mock_session.id = 'cs_test_123'

            with patch('stripe.checkout.Session.retrieve', return_value=mock_session):
                response = client.post(
                    '/api/payments/verify-session',
                    headers=auth_headers,
                    json={'session_id': 'cs_test_123'}
                )

                assert response.status_code == 200
                data = response.get_json()
                assert data['payment_status'] == 'paid'
                assert 'booking' in data

    @pytest.mark.integration
    def test_verify_session_not_paid(self, client, auth_headers, sample_booking, app):
        """Should reject unpaid session."""
        with app.app_context():
            app.config['STRIPE_SECRET_KEY'] = 'sk_test_mock'

            mock_session = MagicMock()
            mock_session.payment_status = 'unpaid'
            mock_session.metadata = {'booking_id': str(sample_booking['id'])}

            with patch('stripe.checkout.Session.retrieve', return_value=mock_session):
                response = client.post(
                    '/api/payments/verify-session',
                    headers=auth_headers,
                    json={'session_id': 'cs_test_123'}
                )

                assert response.status_code == 400
                assert 'not completed' in response.get_json()['error'].lower()


class TestStripeWebhook:
    """Tests for Stripe webhook handler."""

    @pytest.mark.integration
    def test_webhook_no_secret(self, client, app):
        """Should return 503 when webhook secret not configured."""
        response = client.post(
            '/api/payments/webhook',
            data=b'test_payload',
            headers={'Stripe-Signature': 'test_sig'}
        )

        assert response.status_code == 503

    @pytest.mark.integration
    def test_webhook_checkout_completed(self, client, sample_booking, app):
        """Should process checkout.session.completed event."""
        with app.app_context():
            app.config['STRIPE_SECRET_KEY'] = 'sk_test_mock'
            app.config['STRIPE_WEBHOOK_SECRET'] = 'whsec_test'

            mock_event = {
                'type': 'checkout.session.completed',
                'data': {
                    'object': {
                        'metadata': {
                            'booking_id': str(sample_booking['id'])
                        }
                    }
                }
            }

            with patch('stripe.Webhook.construct_event', return_value=mock_event):
                response = client.post(
                    '/api/payments/webhook',
                    data=b'test_payload',
                    headers={'Stripe-Signature': 'test_sig'}
                )

                assert response.status_code == 200

    @pytest.mark.integration
    def test_webhook_payment_intent_succeeded(self, client, app):
        """Should handle payment_intent.succeeded event."""
        with app.app_context():
            app.config['STRIPE_SECRET_KEY'] = 'sk_test_mock'
            app.config['STRIPE_WEBHOOK_SECRET'] = 'whsec_test'

            mock_event = {
                'type': 'payment_intent.succeeded',
                'data': {
                    'object': {
                        'id': 'pi_test_123'
                    }
                }
            }

            with patch('stripe.Webhook.construct_event', return_value=mock_event):
                response = client.post(
                    '/api/payments/webhook',
                    data=b'test_payload',
                    headers={'Stripe-Signature': 'test_sig'}
                )

                assert response.status_code == 200

    @pytest.mark.integration
    def test_webhook_payment_failed(self, client, app):
        """Should handle payment_intent.payment_failed event."""
        with app.app_context():
            app.config['STRIPE_SECRET_KEY'] = 'sk_test_mock'
            app.config['STRIPE_WEBHOOK_SECRET'] = 'whsec_test'

            mock_event = {
                'type': 'payment_intent.payment_failed',
                'data': {
                    'object': {
                        'id': 'pi_test_123'
                    }
                }
            }

            with patch('stripe.Webhook.construct_event', return_value=mock_event):
                response = client.post(
                    '/api/payments/webhook',
                    data=b'test_payload',
                    headers={'Stripe-Signature': 'test_sig'}
                )

                assert response.status_code == 200


class TestRefundMocked:
    """Tests for refund endpoint."""

    @pytest.mark.integration
    def test_refund_success(self, client, auth_headers, sample_booking, app):
        """Should process refund for paid booking."""
        from app.models import db, Booking

        with app.app_context():
            # Mark booking as paid
            booking = Booking.query.get(sample_booking['id'])
            booking.payment_status = 'paid'
            db.session.commit()

            response = client.post(
                '/api/payments/refund',
                headers=auth_headers,
                json={'booking_id': sample_booking['id']}
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['booking']['payment_status'] == 'refunded'
            assert data['booking']['status'] == 'cancelled'

    @pytest.mark.integration
    def test_refund_access_denied(self, client, sample_booking, app):
        """Should deny refund for other user's booking."""
        from app.models import db, User, Booking
        from app.utils.auth import hash_password, generate_token

        with app.app_context():
            # Mark booking as paid
            booking = Booking.query.get(sample_booking['id'])
            booking.payment_status = 'paid'

            # Create another user
            other_user = User(
                email='refund_test@example.com',
                password_hash=hash_password('Password123'),
                name='Refund Test User'
            )
            db.session.add(other_user)
            db.session.commit()
            other_token = generate_token(other_user.id)

            response = client.post(
                '/api/payments/refund',
                headers={'Authorization': f'Bearer {other_token}'},
                json={'booking_id': sample_booking['id']}
            )

            assert response.status_code == 403
