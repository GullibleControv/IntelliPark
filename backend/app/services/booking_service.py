"""
Booking service for managing recurring bookings and waitlist.
Handles automatic booking generation and waitlist notifications.
"""
import logging
from datetime import datetime, date, time, timedelta

from app.models import db, Booking, ParkingSpace, RecurringBooking, Waitlist, User
from app.services.email import send_booking_confirmation
from app.services.websocket import emit_booking_update

logger = logging.getLogger(__name__)


def generate_recurring_bookings(days_ahead=7):
    """
    Generate individual bookings from active recurring booking templates.
    Should be run daily via a scheduler.

    Args:
        days_ahead: Number of days ahead to generate bookings for
    """
    today = date.today()
    end_date = today + timedelta(days=days_ahead)

    active_recurring = RecurringBooking.query.filter(
        RecurringBooking.is_active == True,
        RecurringBooking.valid_from <= end_date,
        (RecurringBooking.valid_until.is_(None)) | (RecurringBooking.valid_until >= today)
    ).all()

    bookings_created = 0

    for recurring in active_recurring:
        current_date = max(today, recurring.valid_from)

        while current_date <= end_date:
            if recurring.valid_until and current_date > recurring.valid_until:
                break

            if should_book_on_date(recurring, current_date):
                # Check if booking already exists
                start_dt = datetime.combine(current_date, recurring.start_time)
                end_dt = datetime.combine(current_date, recurring.end_time)

                existing = Booking.query.filter(
                    Booking.user_id == recurring.user_id,
                    Booking.space_id == recurring.space_id,
                    Booking.start_time == start_dt,
                    Booking.status.in_(['pending', 'confirmed', 'active'])
                ).first()

                if not existing:
                    # Check for conflicts
                    conflict = Booking.query.filter(
                        Booking.space_id == recurring.space_id,
                        Booking.status.in_(['pending', 'confirmed', 'active']),
                        Booking.start_time < end_dt,
                        Booking.end_time > start_dt
                    ).first()

                    if not conflict:
                        # Calculate amount
                        duration_hours = (end_dt - start_dt).total_seconds() / 3600
                        total_amount = duration_hours * recurring.space.hourly_rate

                        booking = Booking(
                            user_id=recurring.user_id,
                            space_id=recurring.space_id,
                            vehicle_number=recurring.vehicle_number,
                            start_time=start_dt,
                            end_time=end_dt,
                            total_amount=round(total_amount, 2),
                            status='confirmed'
                        )
                        db.session.add(booking)
                        bookings_created += 1

            current_date += timedelta(days=1)

    db.session.commit()
    logger.info(f"Generated {bookings_created} bookings from recurring templates")
    return bookings_created


def should_book_on_date(recurring: RecurringBooking, target_date: date) -> bool:
    """Check if a recurring booking should create a booking on the given date."""
    weekday = target_date.weekday()  # 0=Monday, 6=Sunday

    if recurring.pattern == 'daily':
        return True

    if recurring.pattern == 'weekdays':
        return weekday < 5  # Monday-Friday

    if recurring.pattern == 'weekends':
        return weekday >= 5  # Saturday-Sunday

    if recurring.pattern == 'weekly':
        if recurring.days_of_week:
            return weekday in recurring.days_of_week
        # Default to same day as valid_from
        return weekday == recurring.valid_from.weekday()

    return False


def check_waitlist_availability(space_id=None, location=None):
    """
    Check waitlist entries against newly available slots.
    Called when a booking is cancelled or space becomes available.

    Args:
        space_id: Specific space that became available
        location: Location to check (if no specific space)
    """
    now = datetime.utcnow()
    today = now.date()

    # Get waiting entries for this space/location
    query = Waitlist.query.filter(
        Waitlist.status == 'waiting',
        Waitlist.desired_date >= today
    )

    if space_id:
        query = query.filter(
            (Waitlist.space_id == space_id) | (Waitlist.space_id.is_(None))
        )

    if location:
        query = query.filter(
            (Waitlist.location == location) | (Waitlist.location.is_(None))
        )

    waiting_entries = query.order_by(Waitlist.created_at).all()

    notifications_sent = 0

    for entry in waiting_entries:
        # Check if there's availability
        available_space = find_available_space(
            entry.desired_date,
            entry.desired_start_time,
            entry.desired_end_time,
            space_id=entry.space_id,
            location=entry.location or location,
            vehicle_type=entry.vehicle_type
        )

        if available_space:
            # Notify user
            notify_waitlist_user(entry, available_space)
            notifications_sent += 1

    logger.info(f"Sent {notifications_sent} waitlist notifications")
    return notifications_sent


def find_available_space(desired_date, start_time, end_time,
                         space_id=None, location=None, vehicle_type='car'):
    """Find an available parking space for the given time slot."""
    start_dt = datetime.combine(desired_date, start_time)
    end_dt = datetime.combine(desired_date, end_time)

    query = ParkingSpace.query.filter(
        ParkingSpace.is_active == True,
        ParkingSpace.vehicle_type == vehicle_type
    )

    if space_id:
        query = query.filter(ParkingSpace.id == space_id)
    elif location:
        query = query.filter(ParkingSpace.location == location)

    spaces = query.all()

    for space in spaces:
        # Check for conflicting bookings
        conflict = Booking.query.filter(
            Booking.space_id == space.id,
            Booking.status.in_(['pending', 'confirmed', 'active']),
            Booking.start_time < end_dt,
            Booking.end_time > start_dt
        ).first()

        if not conflict:
            return space

    return None


def notify_waitlist_user(waitlist_entry: Waitlist, available_space: ParkingSpace):
    """Notify a user that a waitlisted space is now available."""
    from app.services.email import send_email

    waitlist_entry.status = 'notified'
    waitlist_entry.notified_at = datetime.utcnow()
    # Give user 30 minutes to book
    waitlist_entry.expires_at = datetime.utcnow() + timedelta(minutes=30)

    user = User.query.get(waitlist_entry.user_id)

    if user:
        # Send email notification
        try:
            html = f"""
            <h2>Parking Space Available!</h2>
            <p>Hi {user.name},</p>
            <p>Great news! A parking space matching your waitlist request is now available.</p>
            <ul>
                <li>Location: {available_space.location}</li>
                <li>Space: {available_space.name}</li>
                <li>Date: {waitlist_entry.desired_date}</li>
                <li>Time: {waitlist_entry.desired_start_time} - {waitlist_entry.desired_end_time}</li>
            </ul>
            <p><strong>This spot will only be held for 30 minutes.</strong></p>
            <p>Book now to secure your spot!</p>
            """
            send_email(
                subject='Parking Space Available - Book Now!',
                recipients=[user.email],
                html_body=html
            )
        except Exception as e:
            logger.error(f"Failed to send waitlist notification: {e}")

        # Emit WebSocket notification
        try:
            emit_booking_update(
                user_id=user.id,
                booking_data={
                    'space_id': available_space.id,
                    'space_name': available_space.name,
                    'location': available_space.location,
                    'desired_date': waitlist_entry.desired_date.isoformat(),
                    'waitlist_id': waitlist_entry.id
                },
                event_type='waitlist_available'
            )
        except Exception as e:
            logger.warning(f"Failed to emit waitlist notification: {e}")

    db.session.commit()
    logger.info(f"Notified user {user.email if user else waitlist_entry.user_id} of available space")


def expire_old_waitlist_notifications():
    """Mark expired waitlist notifications as expired."""
    now = datetime.utcnow()

    expired = Waitlist.query.filter(
        Waitlist.status == 'notified',
        Waitlist.expires_at < now
    ).all()

    for entry in expired:
        entry.status = 'expired'

    db.session.commit()

    if expired:
        logger.info(f"Expired {len(expired)} waitlist notifications")

    return len(expired)


def cleanup_old_waitlist_entries(days_old=30):
    """Remove waitlist entries older than specified days."""
    cutoff = date.today() - timedelta(days=days_old)

    deleted = Waitlist.query.filter(
        Waitlist.desired_date < cutoff
    ).delete()

    db.session.commit()

    if deleted:
        logger.info(f"Cleaned up {deleted} old waitlist entries")

    return deleted
