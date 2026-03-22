"""
Email notification service for IntelliPark.
Handles sending booking confirmations, reminders, and alerts.

SECURITY: All user-controlled data is HTML-escaped before rendering
in email templates to prevent XSS attacks.
"""
import logging
from datetime import datetime
from flask import current_app, render_template_string
from flask_mail import Mail, Message
from threading import Thread
from markupsafe import escape as html_escape

logger = logging.getLogger(__name__)


def safe_str(value):
    """
    Safely escape a value for HTML rendering.
    Returns empty string for None values.

    SECURITY: Prevents XSS attacks in email templates by escaping
    HTML special characters (<, >, &, ", ').
    """
    if value is None:
        return ''
    return html_escape(str(value))

# Initialize Mail without app (will be initialized in create_app)
mail = Mail()


def init_mail(app):
    """Initialize Flask-Mail with the app."""
    mail.init_app(app)
    logger.info("Email service initialized")
    return mail


def send_async_email(app, msg):
    """Send email asynchronously."""
    with app.app_context():
        try:
            mail.send(msg)
            logger.info(f"Email sent to {msg.recipients}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")


def send_email(subject, recipients, html_body, text_body=None):
    """
    Send an email.

    Args:
        subject: Email subject
        recipients: List of recipient email addresses
        html_body: HTML content of the email
        text_body: Plain text content (optional)
    """
    if current_app.config.get('TESTING'):
        logger.info(f"Test mode: Would send email to {recipients}")
        return True

    try:
        msg = Message(
            subject=subject,
            recipients=recipients if isinstance(recipients, list) else [recipients],
            html=html_body,
            body=text_body or html_body
        )

        # Send asynchronously to avoid blocking
        Thread(
            target=send_async_email,
            args=(current_app._get_current_object(), msg)
        ).start()

        return True
    except Exception as e:
        logger.error(f"Email send error: {e}")
        return False


# Email Templates

BOOKING_CONFIRMATION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #1a1a2e; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .booking-details { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .detail-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
        .label { color: #666; }
        .value { font-weight: bold; }
        .total { font-size: 1.2em; color: #e94560; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 0.9em; }
        .btn { display: inline-block; padding: 10px 20px; background: #e94560; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>IntelliPark</h1>
            <p>Booking Confirmation</p>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>Your parking booking has been confirmed! Here are the details:</p>

            <div class="booking-details">
                <div class="detail-row">
                    <span class="label">Booking ID</span>
                    <span class="value">#{{ booking_id }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Location</span>
                    <span class="value">{{ location }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Space</span>
                    <span class="value">{{ space_name }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Date</span>
                    <span class="value">{{ booking_date }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Time</span>
                    <span class="value">{{ start_time }} - {{ end_time }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Vehicle</span>
                    <span class="value">{{ vehicle_number or 'Not specified' }}</span>
                </div>
                <div class="detail-row">
                    <span class="label total">Total Amount</span>
                    <span class="value total">${{ "%.2f"|format(total_amount) }}</span>
                </div>
            </div>

            <p>Please arrive at least 5 minutes before your scheduled time.</p>

            <p style="text-align: center; margin-top: 20px;">
                <a href="{{ app_url }}/bookings" class="btn">View My Bookings</a>
            </p>
        </div>
        <div class="footer">
            <p>Thank you for choosing IntelliPark!</p>
            <p>If you have any questions, please contact us at support@intellipark.com</p>
        </div>
    </div>
</body>
</html>
"""

BOOKING_REMINDER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #e94560; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .reminder-box { background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Parking Reminder</h1>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>

            <div class="reminder-box">
                <strong>Your parking reservation starts in {{ minutes_until }} minutes!</strong>
            </div>

            <p><strong>Details:</strong></p>
            <ul>
                <li>Location: {{ location }}</li>
                <li>Space: {{ space_name }}</li>
                <li>Time: {{ start_time }}</li>
            </ul>

            <p>Please make sure to arrive on time to secure your spot.</p>
        </div>
        <div class="footer">
            <p>IntelliPark - Smart Parking Solutions</p>
        </div>
    </div>
</body>
</html>
"""

BOOKING_CANCELLATION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #dc3545; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Booking Cancelled</h1>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>Your parking booking has been cancelled.</p>

            <p><strong>Cancelled Booking Details:</strong></p>
            <ul>
                <li>Booking ID: #{{ booking_id }}</li>
                <li>Location: {{ location }}</li>
                <li>Space: {{ space_name }}</li>
                <li>Original Time: {{ start_time }} - {{ end_time }}</li>
            </ul>

            {% if refund_amount %}
            <p><strong>Refund:</strong> ${{ "%.2f"|format(refund_amount) }} will be credited to your account.</p>
            {% endif %}

            <p>We hope to see you again soon!</p>
        </div>
        <div class="footer">
            <p>IntelliPark - Smart Parking Solutions</p>
        </div>
    </div>
</body>
</html>
"""

PAYMENT_RECEIPT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #28a745; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .receipt { background: white; padding: 20px; border: 1px solid #ddd; margin: 15px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Payment Receipt</h1>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>Thank you for your payment! Here is your receipt:</p>

            <div class="receipt">
                <p><strong>Receipt #{{ receipt_id }}</strong></p>
                <p>Date: {{ payment_date }}</p>
                <hr>
                <p>Booking ID: #{{ booking_id }}</p>
                <p>Location: {{ location }}</p>
                <p>Duration: {{ duration_hours }} hours</p>
                <hr>
                <p><strong>Amount Paid: ${{ "%.2f"|format(amount) }}</strong></p>
                <p>Payment Method: {{ payment_method }}</p>
            </div>
        </div>
        <div class="footer">
            <p>IntelliPark - Smart Parking Solutions</p>
        </div>
    </div>
</body>
</html>
"""


def send_booking_confirmation(user, booking):
    """Send booking confirmation email."""
    try:
        # SECURITY: Escape all user-controlled data to prevent XSS
        html = render_template_string(
            BOOKING_CONFIRMATION_TEMPLATE,
            user_name=safe_str(user.name),
            booking_id=booking.id,
            location=safe_str(booking.space.location),
            space_name=safe_str(booking.space.name),
            booking_date=booking.start_time.strftime('%B %d, %Y'),
            start_time=booking.start_time.strftime('%I:%M %p'),
            end_time=booking.end_time.strftime('%I:%M %p'),
            vehicle_number=safe_str(booking.vehicle_number),
            total_amount=booking.total_amount,
            app_url=current_app.config.get('APP_URL', 'http://localhost:5000')
        )

        return send_email(
            subject=f'Booking Confirmed - #{booking.id}',
            recipients=[user.email],
            html_body=html
        )
    except Exception as e:
        logger.error(f"Failed to send booking confirmation: {e}")
        return False


def send_booking_reminder(user, booking, minutes_until=30):
    """Send booking reminder email."""
    try:
        # SECURITY: Escape all user-controlled data to prevent XSS
        html = render_template_string(
            BOOKING_REMINDER_TEMPLATE,
            user_name=safe_str(user.name),
            minutes_until=minutes_until,
            location=safe_str(booking.space.location),
            space_name=safe_str(booking.space.name),
            start_time=booking.start_time.strftime('%I:%M %p')
        )

        return send_email(
            subject=f'Reminder: Your parking reservation starts in {minutes_until} minutes',
            recipients=[user.email],
            html_body=html
        )
    except Exception as e:
        logger.error(f"Failed to send booking reminder: {e}")
        return False


def send_booking_cancellation(user, booking, refund_amount=None):
    """Send booking cancellation email."""
    try:
        # SECURITY: Escape all user-controlled data to prevent XSS
        html = render_template_string(
            BOOKING_CANCELLATION_TEMPLATE,
            user_name=safe_str(user.name),
            booking_id=booking.id,
            location=safe_str(booking.space.location),
            space_name=safe_str(booking.space.name),
            start_time=booking.start_time.strftime('%I:%M %p'),
            end_time=booking.end_time.strftime('%I:%M %p'),
            refund_amount=refund_amount
        )

        return send_email(
            subject=f'Booking Cancelled - #{booking.id}',
            recipients=[user.email],
            html_body=html
        )
    except Exception as e:
        logger.error(f"Failed to send cancellation email: {e}")
        return False


def send_payment_receipt(user, booking, payment_data):
    """Send payment receipt email."""
    try:
        # SECURITY: Escape all user-controlled data to prevent XSS
        html = render_template_string(
            PAYMENT_RECEIPT_TEMPLATE,
            user_name=safe_str(user.name),
            receipt_id=safe_str(payment_data.get('receipt_id')),
            payment_date=datetime.utcnow().strftime('%B %d, %Y'),
            booking_id=booking.id,
            location=safe_str(booking.space.location),
            duration_hours=round((booking.end_time - booking.start_time).total_seconds() / 3600, 1),
            amount=payment_data.get('amount', booking.total_amount),
            payment_method=safe_str(payment_data.get('payment_method', 'Card'))
        )

        return send_email(
            subject=f'Payment Receipt - IntelliPark',
            recipients=[user.email],
            html_body=html
        )
    except Exception as e:
        logger.error(f"Failed to send payment receipt: {e}")
        return False
