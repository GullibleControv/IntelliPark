"""
Unit tests for email service.
Tests email sending and templates.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock


class TestEmailService:
    """Tests for email service functions."""

    def test_send_email_basic(self, app):
        """Should send email without errors."""
        with app.app_context():
            from app.services.email import send_email

            # In test mode, email is not actually sent
            result = send_email(
                subject='Test Subject',
                recipients=['test@example.com'],
                html_body='<p>Test content</p>'
            )

            # Should return True in test mode
            assert result is True

    def test_send_booking_confirmation(self, app, sample_booking, sample_user):
        """Should send booking confirmation email."""
        with app.app_context():
            from app.services.email import send_booking_confirmation
            from app.models import Booking, User

            booking = Booking.query.get(sample_booking['id'])
            user = User.query.get(sample_user['id'])

            # Should not raise an error
            result = send_booking_confirmation(user, booking)
            assert result is True

    def test_send_booking_reminder(self, app, sample_booking, sample_user):
        """Should send booking reminder email."""
        with app.app_context():
            from app.services.email import send_booking_reminder
            from app.models import Booking, User

            booking = Booking.query.get(sample_booking['id'])
            user = User.query.get(sample_user['id'])

            # Should not raise an error
            result = send_booking_reminder(user, booking, minutes_until=30)
            assert result is True

    def test_send_booking_cancellation(self, app, sample_booking, sample_user):
        """Should send booking cancellation email."""
        with app.app_context():
            from app.services.email import send_booking_cancellation
            from app.models import Booking, User

            booking = Booking.query.get(sample_booking['id'])
            user = User.query.get(sample_user['id'])

            # Should not raise an error
            result = send_booking_cancellation(user, booking, refund_amount=50.0)
            assert result is True

    def test_send_payment_receipt(self, app, sample_booking, sample_user):
        """Should send payment receipt email."""
        with app.app_context():
            from app.services.email import send_payment_receipt
            from app.models import Booking, User

            booking = Booking.query.get(sample_booking['id'])
            user = User.query.get(sample_user['id'])

            payment_data = {
                'receipt_id': 'RCP-123456',
                'amount': 100.00,
                'payment_method': 'Card'
            }

            # Should not raise an error
            result = send_payment_receipt(user, booking, payment_data)
            assert result is True


class TestEmailTemplates:
    """Tests for email template rendering."""

    def test_booking_confirmation_template_contains_required_info(self, app):
        """Booking confirmation template should include required placeholders."""
        with app.app_context():
            from app.services.email import BOOKING_CONFIRMATION_TEMPLATE

            # Check for Jinja2 template variables (uses {{ }} syntax)
            assert '{{ user_name }}' in BOOKING_CONFIRMATION_TEMPLATE
            assert '{{ space_name }}' in BOOKING_CONFIRMATION_TEMPLATE
            assert '{{ location }}' in BOOKING_CONFIRMATION_TEMPLATE
            assert '{{ booking_date }}' in BOOKING_CONFIRMATION_TEMPLATE
            assert '{{ start_time }}' in BOOKING_CONFIRMATION_TEMPLATE
            assert '{{ end_time }}' in BOOKING_CONFIRMATION_TEMPLATE

    def test_booking_reminder_template_contains_required_info(self, app):
        """Booking reminder template should include required placeholders."""
        with app.app_context():
            from app.services.email import BOOKING_REMINDER_TEMPLATE

            assert '{{ user_name }}' in BOOKING_REMINDER_TEMPLATE
            assert '{{ space_name }}' in BOOKING_REMINDER_TEMPLATE

    def test_payment_receipt_template_contains_required_info(self, app):
        """Payment receipt template should include required placeholders."""
        with app.app_context():
            from app.services.email import PAYMENT_RECEIPT_TEMPLATE

            assert '{{ user_name }}' in PAYMENT_RECEIPT_TEMPLATE
            assert 'amount' in PAYMENT_RECEIPT_TEMPLATE  # Used with format filter
            assert '{{ receipt_id }}' in PAYMENT_RECEIPT_TEMPLATE

    def test_cancellation_template_contains_required_info(self, app):
        """Cancellation template should include required placeholders."""
        with app.app_context():
            from app.services.email import BOOKING_CANCELLATION_TEMPLATE

            assert '{{ user_name }}' in BOOKING_CANCELLATION_TEMPLATE
            assert '{{ booking_id }}' in BOOKING_CANCELLATION_TEMPLATE
            assert '{{ location }}' in BOOKING_CANCELLATION_TEMPLATE
