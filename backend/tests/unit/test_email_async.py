"""
Unit tests for async email sending.
Tests email sending with mock mail client.
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


class TestAsyncEmailSending:
    """Tests for async email functionality."""

    def test_send_async_email(self, app):
        """Should send email asynchronously."""
        with app.app_context():
            # Temporarily disable testing mode
            original_testing = app.config['TESTING']
            app.config['TESTING'] = False

            from app.services.email import send_email

            with patch('app.services.email.mail') as mock_mail:
                with patch('app.services.email.Thread') as mock_thread:
                    mock_mail.send = MagicMock()
                    mock_thread_instance = MagicMock()
                    mock_thread.return_value = mock_thread_instance

                    result = send_email(
                        subject='Test Subject',
                        recipients=['test@example.com'],
                        html_body='<p>Test</p>'
                    )

                    # Restore testing mode
                    app.config['TESTING'] = original_testing

                    assert result is True
                    mock_thread.assert_called_once()
                    mock_thread_instance.start.assert_called_once()

    def test_send_email_handles_exception(self, app):
        """Should handle email sending exceptions gracefully."""
        with app.app_context():
            original_testing = app.config['TESTING']
            app.config['TESTING'] = False

            from app.services.email import send_email

            with patch('app.services.email.mail') as mock_mail:
                with patch('app.services.email.Thread', side_effect=Exception('Email error')):
                    result = send_email(
                        subject='Test Subject',
                        recipients=['test@example.com'],
                        html_body='<p>Test</p>'
                    )

                    app.config['TESTING'] = original_testing

                    # Should return False on error
                    assert result is False


class TestAsyncEmailRunner:
    """Tests for send_async_email function."""

    def test_send_async_email_success(self, app):
        """Should send email in async context."""
        with app.app_context():
            from app.services.email import send_async_email, Message

            with patch('app.services.email.mail') as mock_mail:
                mock_mail.send = MagicMock()

                msg = MagicMock()
                msg.recipients = ['test@example.com']

                # Call directly (not through thread)
                send_async_email(app, msg)

                mock_mail.send.assert_called_once_with(msg)

    def test_send_async_email_failure(self, app):
        """Should handle async email failures."""
        with app.app_context():
            from app.services.email import send_async_email

            with patch('app.services.email.mail') as mock_mail:
                mock_mail.send = MagicMock(side_effect=Exception('SMTP Error'))

                msg = MagicMock()
                msg.recipients = ['test@example.com']

                # Should not raise, just log error
                send_async_email(app, msg)
