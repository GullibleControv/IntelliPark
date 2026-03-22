"""
Payment routes for Stripe integration.
Handles checkout sessions, webhooks, and payment status.
"""
from flask import Blueprint, request, jsonify, current_app
import logging
import stripe

from app.models import db, Booking, User
from app.utils.auth import token_required
from app.services.email import send_payment_receipt

logger = logging.getLogger(__name__)

payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')


def get_stripe():
    """Initialize and return Stripe with the secret key."""
    stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
    return stripe


@payments_bp.route('/config', methods=['GET'])
def get_stripe_config():
    """Get Stripe publishable key for frontend."""
    publishable_key = current_app.config.get('STRIPE_PUBLISHABLE_KEY')

    if not publishable_key:
        return jsonify({'error': 'Stripe not configured'}), 503

    return jsonify({
        'publishable_key': publishable_key
    })


@payments_bp.route('/create-checkout-session', methods=['POST'])
@token_required
def create_checkout_session():
    """
    Create a Stripe checkout session for a booking.

    Request body:
        - booking_id: ID of the booking to pay for

    Returns:
        - session_id: Stripe checkout session ID
        - url: Redirect URL for checkout
    """
    try:
        stripe_client = get_stripe()

        if not stripe_client.api_key:
            return jsonify({'error': 'Payment system not configured'}), 503

        data = request.get_json()

        if not data or not data.get('booking_id'):
            return jsonify({'error': 'booking_id is required'}), 400

        booking_id = data['booking_id']
        booking = Booking.query.get(booking_id)

        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        # Verify user owns this booking
        if booking.user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403

        # Check if already paid
        if booking.payment_status == 'paid':
            return jsonify({'error': 'Booking already paid'}), 400

        # Check if booking is valid for payment
        if booking.status not in ['pending', 'confirmed']:
            return jsonify({'error': f'Cannot pay for {booking.status} booking'}), 400

        # Get user info
        user = User.query.get(request.user_id)

        # Calculate duration
        duration_hours = round(
            (booking.end_time - booking.start_time).total_seconds() / 3600, 1
        )

        # Create Stripe checkout session
        app_url = current_app.config.get('APP_URL', 'http://localhost:5000')

        session = stripe_client.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Parking at {booking.space.location}',
                        'description': f'Space {booking.space.name} - {duration_hours} hours',
                    },
                    'unit_amount': int(booking.total_amount * 100),  # Stripe uses cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{app_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&booking_id={booking_id}',
            cancel_url=f'{app_url}/payment-cancelled?booking_id={booking_id}',
            customer_email=user.email if user else None,
            metadata={
                'booking_id': str(booking_id),
                'user_id': str(request.user_id)
            }
        )

        logger.info(f"Created checkout session {session.id} for booking {booking_id}")

        return jsonify({
            'session_id': session.id,
            'url': session.url
        })

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        return jsonify({'error': 'Payment processing error'}), 500
    except Exception as e:
        logger.error(f"Create checkout error: {e}")
        return jsonify({'error': 'Failed to create checkout session'}), 500


@payments_bp.route('/verify-session', methods=['POST'])
@token_required
def verify_session():
    """
    Verify a Stripe checkout session and update booking.

    Request body:
        - session_id: Stripe checkout session ID

    Returns:
        - booking: Updated booking data
        - payment_status: Payment status
    """
    try:
        stripe_client = get_stripe()

        data = request.get_json()

        if not data or not data.get('session_id'):
            return jsonify({'error': 'session_id is required'}), 400

        session_id = data['session_id']

        # Retrieve session from Stripe
        session = stripe_client.checkout.Session.retrieve(session_id)

        if session.payment_status != 'paid':
            return jsonify({
                'error': 'Payment not completed',
                'payment_status': session.payment_status
            }), 400

        # Get booking from metadata
        booking_id = session.metadata.get('booking_id')
        if not booking_id:
            return jsonify({'error': 'Invalid session'}), 400

        booking = Booking.query.get(int(booking_id))
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        # Verify user owns this booking
        if booking.user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403

        # Update booking payment status and store payment intent for refunds
        if booking.payment_status != 'paid':
            booking.payment_status = 'paid'
            booking.status = 'confirmed'
            # Store the payment intent ID for potential refunds
            booking.stripe_payment_intent_id = session.payment_intent
            db.session.commit()

            logger.info(f"Payment confirmed for booking {booking_id}, intent: {session.payment_intent}")

            # Send receipt email
            user = User.query.get(request.user_id)
            if user:
                try:
                    send_payment_receipt(user, booking, {
                        'receipt_id': session.id[:16],
                        'amount': booking.total_amount,
                        'payment_method': 'Card'
                    })
                except Exception as email_error:
                    logger.warning(f"Failed to send receipt: {email_error}")

        return jsonify({
            'message': 'Payment verified',
            'booking': booking.to_dict(),
            'payment_status': 'paid'
        })

    except stripe.error.StripeError as e:
        logger.error(f"Stripe verification error: {e}")
        return jsonify({'error': 'Payment verification failed'}), 500
    except Exception as e:
        logger.error(f"Verify session error: {e}")
        return jsonify({'error': 'Failed to verify payment'}), 500


@payments_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events.
    Used for asynchronous payment confirmations.
    """
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')

    if not webhook_secret:
        logger.warning("Stripe webhook secret not configured")
        return jsonify({'error': 'Webhook not configured'}), 503

    try:
        stripe_client = get_stripe()
        event = stripe_client.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_completed(session)

    elif event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        logger.info(f"Payment intent succeeded: {payment_intent['id']}")

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        logger.warning(f"Payment failed: {payment_intent['id']}")

    return jsonify({'status': 'success'})


def handle_checkout_completed(session):
    """Process completed checkout session from webhook."""
    booking_id = session.get('metadata', {}).get('booking_id')

    if not booking_id:
        logger.warning("Webhook received without booking_id")
        return

    booking = Booking.query.get(int(booking_id))
    if not booking:
        logger.warning(f"Booking {booking_id} not found for webhook")
        return

    if booking.payment_status != 'paid':
        booking.payment_status = 'paid'
        booking.status = 'confirmed'
        db.session.commit()
        logger.info(f"Webhook: Payment confirmed for booking {booking_id}")


@payments_bp.route('/booking/<int:booking_id>/status', methods=['GET'])
@token_required
def get_payment_status(booking_id):
    """Get payment status for a booking."""
    booking = Booking.query.get(booking_id)

    if not booking:
        return jsonify({'error': 'Booking not found'}), 404

    if booking.user_id != request.user_id:
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'booking_id': booking.id,
        'payment_status': booking.payment_status,
        'total_amount': booking.total_amount,
        'status': booking.status
    })


@payments_bp.route('/refund', methods=['POST'])
@token_required
def create_refund():
    """
    Create a refund for a paid booking.
    Note: Full refund implementation requires storing Stripe payment intent ID.
    """
    try:
        data = request.get_json()

        if not data or not data.get('booking_id'):
            return jsonify({'error': 'booking_id is required'}), 400

        booking = Booking.query.get(data['booking_id'])

        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        if booking.user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403

        if booking.payment_status != 'paid':
            return jsonify({'error': 'Booking is not paid'}), 400

        # Check if we have a payment intent to refund
        if not booking.stripe_payment_intent_id:
            logger.error(f"No payment intent found for booking {booking.id}")
            return jsonify({'error': 'Payment information not found. Please contact support.'}), 400

        # Process refund through Stripe
        stripe_client = get_stripe()
        try:
            refund = stripe_client.Refund.create(
                payment_intent=booking.stripe_payment_intent_id,
                reason='requested_by_customer'
            )

            if refund.status == 'succeeded':
                booking.payment_status = 'refunded'
                booking.status = 'cancelled'
                db.session.commit()

                logger.info(f"Refund processed for booking {booking.id}, refund_id: {refund.id}")

                return jsonify({
                    'message': 'Refund processed successfully',
                    'refund_id': refund.id,
                    'booking': booking.to_dict()
                })
            elif refund.status == 'pending':
                booking.payment_status = 'refund_pending'
                db.session.commit()

                return jsonify({
                    'message': 'Refund is being processed',
                    'refund_id': refund.id,
                    'booking': booking.to_dict()
                })
            else:
                logger.error(f"Unexpected refund status: {refund.status}")
                return jsonify({'error': 'Refund failed. Please contact support.'}), 500

        except stripe_client.error.InvalidRequestError as e:
            logger.error(f"Stripe refund error: {e}")
            return jsonify({'error': 'Unable to process refund. Payment may have already been refunded.'}), 400

    except Exception as e:
        logger.error(f"Refund error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to process refund'}), 500
