from flask import Blueprint, request, jsonify
from datetime import datetime, date, time as dt_time
import logging

from app.models import db, Booking, ParkingSpace, User, RecurringBooking, Waitlist
from app.utils.auth import token_required
from app.utils.validators import validate_vehicle_number, sanitize_string
from app.services.email import send_booking_confirmation, send_booking_cancellation
from app.services.booking_service import check_waitlist_availability

logger = logging.getLogger(__name__)

booking_bp = Blueprint('booking', __name__, url_prefix='/api/bookings')


@booking_bp.route('', methods=['POST'])
@token_required
def create_booking():
    """Create a new parking booking."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Required fields
        space_id = data.get('space_id')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')

        if not all([space_id, start_time_str, end_time_str]):
            return jsonify({'error': 'space_id, start_time, and end_time are required'}), 400

        # Optional fields
        vehicle_number = sanitize_string(data.get('vehicle_number', ''))

        if vehicle_number and not validate_vehicle_number(vehicle_number):
            return jsonify({'error': 'Invalid vehicle number format'}), 400

        # Validate parking space
        space = ParkingSpace.query.get(space_id)
        if not space:
            return jsonify({'error': 'Parking space not found'}), 404

        if not space.is_active:
            return jsonify({'error': 'Parking space is not available'}), 400

        # Parse datetime
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid datetime format. Use ISO 8601 format.'}), 400

        # Validate times
        if end_time <= start_time:
            return jsonify({'error': 'End time must be after start time'}), 400

        if start_time < datetime.utcnow():
            return jsonify({'error': 'Cannot book for past times'}), 400

        # Check for conflicting bookings
        conflict = Booking.query.filter(
            Booking.space_id == space_id,
            Booking.status.in_(['pending', 'confirmed', 'active']),
            Booking.start_time < end_time,
            Booking.end_time > start_time
        ).first()

        if conflict:
            return jsonify({'error': 'This time slot is already booked'}), 409

        # Calculate total amount
        duration_hours = (end_time - start_time).total_seconds() / 3600
        total_amount = round(duration_hours * space.hourly_rate, 2)

        # Create booking
        booking = Booking(
            user_id=request.user_id,
            space_id=space_id,
            vehicle_number=vehicle_number.upper() if vehicle_number else None,
            start_time=start_time,
            end_time=end_time,
            total_amount=total_amount,
            status='confirmed'
        )

        db.session.add(booking)
        db.session.commit()

        logger.info(f"New booking created: {booking.id} for space {space.name}")

        # Send confirmation email
        user = User.query.get(request.user_id)
        if user:
            try:
                send_booking_confirmation(user, booking)
            except Exception as email_error:
                logger.warning(f"Failed to send confirmation email: {email_error}")

        return jsonify({
            'message': 'Booking created successfully',
            'booking': booking.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Create booking error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create booking'}), 500


@booking_bp.route('', methods=['GET'])
@token_required
def get_user_bookings():
    """Get all bookings for the current user."""
    try:
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Limit per_page
        per_page = min(per_page, 50)

        query = Booking.query.filter_by(user_id=request.user_id)

        if status:
            query = query.filter_by(status=status)

        # Order by most recent first
        query = query.order_by(Booking.created_at.desc())

        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'bookings': [b.to_dict() for b in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })

    except Exception as e:
        logger.error(f"Get bookings error: {e}")
        return jsonify({'error': 'Failed to fetch bookings'}), 500


@booking_bp.route('/<int:booking_id>', methods=['GET'])
@token_required
def get_booking(booking_id):
    """Get a specific booking."""
    try:
        booking = Booking.query.get(booking_id)

        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        # Ensure user owns this booking
        if booking.user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403

        return jsonify({'booking': booking.to_dict()})

    except Exception as e:
        logger.error(f"Get booking error: {e}")
        return jsonify({'error': 'Failed to fetch booking'}), 500


@booking_bp.route('/<int:booking_id>/cancel', methods=['POST'])
@token_required
def cancel_booking(booking_id):
    """Cancel a booking."""
    try:
        booking = Booking.query.get(booking_id)

        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        # Ensure user owns this booking
        if booking.user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403

        # Check if already cancelled
        if booking.status == 'cancelled':
            return jsonify({'error': 'Booking is already cancelled'}), 400

        # Check if booking has already started
        if booking.status == 'active':
            return jsonify({'error': 'Cannot cancel an active booking'}), 400

        if booking.status == 'completed':
            return jsonify({'error': 'Cannot cancel a completed booking'}), 400

        # Cancel the booking
        booking.status = 'cancelled'
        refund_amount = None

        # Handle refund logic if payment was made
        if booking.payment_status == 'paid':
            booking.payment_status = 'refunded'
            refund_amount = booking.total_amount

        db.session.commit()

        logger.info(f"Booking cancelled: {booking.id}")

        # Send cancellation email
        user = User.query.get(request.user_id)
        if user:
            try:
                send_booking_cancellation(user, booking, refund_amount)
            except Exception as email_error:
                logger.warning(f"Failed to send cancellation email: {email_error}")

        # Check waitlist for newly available slot
        try:
            check_waitlist_availability(
                space_id=booking.space_id,
                location=booking.space.location if booking.space else None
            )
        except Exception as waitlist_error:
            logger.warning(f"Waitlist check failed: {waitlist_error}")

        return jsonify({
            'message': 'Booking cancelled successfully',
            'booking': booking.to_dict()
        })

    except Exception as e:
        logger.error(f"Cancel booking error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to cancel booking'}), 500


@booking_bp.route('/<int:booking_id>/start', methods=['POST'])
@token_required
def start_booking(booking_id):
    """Mark a booking as active (user has arrived)."""
    try:
        booking = Booking.query.get(booking_id)

        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        if booking.user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403

        if booking.status != 'confirmed':
            return jsonify({'error': f'Cannot start a {booking.status} booking'}), 400

        booking.status = 'active'
        db.session.commit()

        logger.info(f"Booking started: {booking.id}")

        return jsonify({
            'message': 'Booking started',
            'booking': booking.to_dict()
        })

    except Exception as e:
        logger.error(f"Start booking error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to start booking'}), 500


@booking_bp.route('/<int:booking_id>/complete', methods=['POST'])
@token_required
def complete_booking(booking_id):
    """Mark a booking as completed (user has left)."""
    try:
        booking = Booking.query.get(booking_id)

        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        if booking.user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403

        if booking.status != 'active':
            return jsonify({'error': f'Cannot complete a {booking.status} booking'}), 400

        booking.status = 'completed'
        db.session.commit()

        logger.info(f"Booking completed: {booking.id}")

        return jsonify({
            'message': 'Booking completed',
            'booking': booking.to_dict()
        })

    except Exception as e:
        logger.error(f"Complete booking error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to complete booking'}), 500


@booking_bp.route('/active', methods=['GET'])
@token_required
def get_active_bookings():
    """Get user's currently active bookings."""
    try:
        bookings = Booking.query.filter_by(
            user_id=request.user_id,
            status='active'
        ).all()

        return jsonify({
            'bookings': [b.to_dict() for b in bookings],
            'count': len(bookings)
        })

    except Exception as e:
        logger.error(f"Get active bookings error: {e}")
        return jsonify({'error': 'Failed to fetch active bookings'}), 500


@booking_bp.route('/upcoming', methods=['GET'])
@token_required
def get_upcoming_bookings():
    """Get user's upcoming confirmed bookings."""
    try:
        now = datetime.utcnow()

        bookings = Booking.query.filter(
            Booking.user_id == request.user_id,
            Booking.status == 'confirmed',
            Booking.start_time > now
        ).order_by(Booking.start_time).limit(5).all()

        return jsonify({
            'bookings': [b.to_dict() for b in bookings],
            'count': len(bookings)
        })

    except Exception as e:
        logger.error(f"Get upcoming bookings error: {e}")
        return jsonify({'error': 'Failed to fetch upcoming bookings'}), 500


# ============== Recurring Bookings ==============

@booking_bp.route('/recurring', methods=['POST'])
@token_required
def create_recurring_booking():
    """Create a recurring booking template."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Required fields
        space_id = data.get('space_id')
        pattern = data.get('pattern')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        valid_from_str = data.get('valid_from')

        if not all([space_id, pattern, start_time_str, end_time_str, valid_from_str]):
            return jsonify({
                'error': 'space_id, pattern, start_time, end_time, and valid_from are required'
            }), 400

        # Validate pattern
        valid_patterns = ['daily', 'weekly', 'weekdays', 'weekends']
        if pattern not in valid_patterns:
            return jsonify({
                'error': f'Invalid pattern. Must be one of: {", ".join(valid_patterns)}'
            }), 400

        # Validate space
        space = ParkingSpace.query.get(space_id)
        if not space or not space.is_active:
            return jsonify({'error': 'Parking space not found or inactive'}), 404

        # Parse times
        try:
            start_time = dt_time.fromisoformat(start_time_str)
            end_time = dt_time.fromisoformat(end_time_str)
            valid_from = date.fromisoformat(valid_from_str)
        except ValueError:
            return jsonify({'error': 'Invalid time/date format'}), 400

        if end_time <= start_time:
            return jsonify({'error': 'End time must be after start time'}), 400

        # Optional fields
        valid_until_str = data.get('valid_until')
        valid_until = date.fromisoformat(valid_until_str) if valid_until_str else None

        days_of_week = data.get('days_of_week')
        vehicle_number = sanitize_string(data.get('vehicle_number', ''))

        if vehicle_number and not validate_vehicle_number(vehicle_number):
            return jsonify({'error': 'Invalid vehicle number format'}), 400

        recurring = RecurringBooking(
            user_id=request.user_id,
            space_id=space_id,
            pattern=pattern,
            start_time=start_time,
            end_time=end_time,
            days_of_week=days_of_week,
            valid_from=valid_from,
            valid_until=valid_until,
            vehicle_number=vehicle_number.upper() if vehicle_number else None,
            is_active=True
        )

        db.session.add(recurring)
        db.session.commit()

        logger.info(f"Recurring booking created: {recurring.id}")

        return jsonify({
            'message': 'Recurring booking created',
            'recurring_booking': recurring.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Create recurring booking error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create recurring booking'}), 500


@booking_bp.route('/recurring', methods=['GET'])
@token_required
def get_recurring_bookings():
    """Get all recurring bookings for the current user."""
    try:
        active_only = request.args.get('active', 'true').lower() == 'true'

        query = RecurringBooking.query.filter_by(user_id=request.user_id)

        if active_only:
            query = query.filter_by(is_active=True)

        recurring = query.order_by(RecurringBooking.created_at.desc()).all()

        return jsonify({
            'recurring_bookings': [r.to_dict() for r in recurring],
            'count': len(recurring)
        })

    except Exception as e:
        logger.error(f"Get recurring bookings error: {e}")
        return jsonify({'error': 'Failed to fetch recurring bookings'}), 500


@booking_bp.route('/recurring/<int:recurring_id>', methods=['DELETE'])
@token_required
def cancel_recurring_booking(recurring_id):
    """Cancel (deactivate) a recurring booking."""
    try:
        recurring = RecurringBooking.query.get(recurring_id)

        if not recurring:
            return jsonify({'error': 'Recurring booking not found'}), 404

        if recurring.user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403

        recurring.is_active = False
        db.session.commit()

        logger.info(f"Recurring booking cancelled: {recurring_id}")

        return jsonify({
            'message': 'Recurring booking cancelled',
            'recurring_booking': recurring.to_dict()
        })

    except Exception as e:
        logger.error(f"Cancel recurring booking error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to cancel recurring booking'}), 500


# ============== Waitlist ==============

@booking_bp.route('/waitlist', methods=['POST'])
@token_required
def join_waitlist():
    """Join the waitlist for a parking space."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Required fields
        desired_date_str = data.get('desired_date')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')

        if not all([desired_date_str, start_time_str, end_time_str]):
            return jsonify({
                'error': 'desired_date, start_time, and end_time are required'
            }), 400

        # At least one of space_id or location must be provided
        space_id = data.get('space_id')
        location = data.get('location')

        if not space_id and not location:
            return jsonify({
                'error': 'Either space_id or location must be provided'
            }), 400

        # Parse times
        try:
            desired_date = date.fromisoformat(desired_date_str)
            start_time = dt_time.fromisoformat(start_time_str)
            end_time = dt_time.fromisoformat(end_time_str)
        except ValueError:
            return jsonify({'error': 'Invalid date/time format'}), 400

        if desired_date < date.today():
            return jsonify({'error': 'Cannot join waitlist for past dates'}), 400

        if end_time <= start_time:
            return jsonify({'error': 'End time must be after start time'}), 400

        # Check if already on waitlist
        existing = Waitlist.query.filter(
            Waitlist.user_id == request.user_id,
            Waitlist.desired_date == desired_date,
            Waitlist.status == 'waiting'
        ).first()

        if existing:
            return jsonify({
                'error': 'You are already on the waitlist for this date'
            }), 409

        vehicle_type = data.get('vehicle_type', 'car')

        waitlist_entry = Waitlist(
            user_id=request.user_id,
            space_id=space_id,
            location=location,
            desired_date=desired_date,
            desired_start_time=start_time,
            desired_end_time=end_time,
            vehicle_type=vehicle_type,
            status='waiting'
        )

        db.session.add(waitlist_entry)
        db.session.commit()

        logger.info(f"User {request.user_id} joined waitlist: {waitlist_entry.id}")

        return jsonify({
            'message': 'Added to waitlist',
            'waitlist_entry': waitlist_entry.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Join waitlist error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to join waitlist'}), 500


@booking_bp.route('/waitlist', methods=['GET'])
@token_required
def get_waitlist_entries():
    """Get user's waitlist entries."""
    try:
        status = request.args.get('status')

        query = Waitlist.query.filter_by(user_id=request.user_id)

        if status:
            query = query.filter_by(status=status)

        entries = query.order_by(Waitlist.desired_date).all()

        return jsonify({
            'waitlist_entries': [e.to_dict() for e in entries],
            'count': len(entries)
        })

    except Exception as e:
        logger.error(f"Get waitlist error: {e}")
        return jsonify({'error': 'Failed to fetch waitlist'}), 500


@booking_bp.route('/waitlist/<int:entry_id>', methods=['DELETE'])
@token_required
def leave_waitlist(entry_id):
    """Remove entry from waitlist."""
    try:
        entry = Waitlist.query.get(entry_id)

        if not entry:
            return jsonify({'error': 'Waitlist entry not found'}), 404

        if entry.user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403

        db.session.delete(entry)
        db.session.commit()

        logger.info(f"Waitlist entry removed: {entry_id}")

        return jsonify({'message': 'Removed from waitlist'})

    except Exception as e:
        logger.error(f"Leave waitlist error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to leave waitlist'}), 500
