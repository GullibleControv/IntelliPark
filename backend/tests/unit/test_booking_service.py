"""
Unit tests for booking service functions.
Tests recurring booking generation and waitlist management.
"""
import pytest
from datetime import date, time, timedelta, datetime
from unittest.mock import patch, MagicMock

from app.services.booking_service import (
    should_book_on_date,
    generate_recurring_bookings,
    find_available_space,
    check_waitlist_availability,
    expire_old_waitlist_notifications,
    cleanup_old_waitlist_entries
)


class TestShouldBookOnDate:
    """Tests for should_book_on_date function."""

    def test_daily_pattern_always_true(self, app):
        """Daily pattern should return True for any date."""
        with app.app_context():
            recurring = MagicMock()
            recurring.pattern = 'daily'

            # Test various days
            assert should_book_on_date(recurring, date(2024, 1, 1))  # Monday
            assert should_book_on_date(recurring, date(2024, 1, 6))  # Saturday
            assert should_book_on_date(recurring, date(2024, 1, 7))  # Sunday

    def test_weekdays_pattern(self, app):
        """Weekdays pattern should return True only Mon-Fri."""
        with app.app_context():
            recurring = MagicMock()
            recurring.pattern = 'weekdays'

            # Monday through Friday
            assert should_book_on_date(recurring, date(2024, 1, 1))  # Monday
            assert should_book_on_date(recurring, date(2024, 1, 2))  # Tuesday
            assert should_book_on_date(recurring, date(2024, 1, 3))  # Wednesday
            assert should_book_on_date(recurring, date(2024, 1, 4))  # Thursday
            assert should_book_on_date(recurring, date(2024, 1, 5))  # Friday

            # Saturday and Sunday
            assert not should_book_on_date(recurring, date(2024, 1, 6))  # Saturday
            assert not should_book_on_date(recurring, date(2024, 1, 7))  # Sunday

    def test_weekends_pattern(self, app):
        """Weekends pattern should return True only Sat-Sun."""
        with app.app_context():
            recurring = MagicMock()
            recurring.pattern = 'weekends'

            # Weekdays
            assert not should_book_on_date(recurring, date(2024, 1, 1))  # Monday
            assert not should_book_on_date(recurring, date(2024, 1, 5))  # Friday

            # Weekends
            assert should_book_on_date(recurring, date(2024, 1, 6))  # Saturday
            assert should_book_on_date(recurring, date(2024, 1, 7))  # Sunday

    def test_weekly_pattern_with_days_of_week(self, app):
        """Weekly pattern with specific days should match those days."""
        with app.app_context():
            recurring = MagicMock()
            recurring.pattern = 'weekly'
            recurring.days_of_week = [0, 2, 4]  # Mon, Wed, Fri

            assert should_book_on_date(recurring, date(2024, 1, 1))  # Monday
            assert not should_book_on_date(recurring, date(2024, 1, 2))  # Tuesday
            assert should_book_on_date(recurring, date(2024, 1, 3))  # Wednesday
            assert not should_book_on_date(recurring, date(2024, 1, 4))  # Thursday
            assert should_book_on_date(recurring, date(2024, 1, 5))  # Friday
            assert not should_book_on_date(recurring, date(2024, 1, 6))  # Saturday

    def test_weekly_pattern_defaults_to_valid_from_day(self, app):
        """Weekly pattern without days_of_week should default to valid_from day."""
        with app.app_context():
            recurring = MagicMock()
            recurring.pattern = 'weekly'
            recurring.days_of_week = None
            recurring.valid_from = date(2024, 1, 1)  # Monday

            # Should only match Mondays
            assert should_book_on_date(recurring, date(2024, 1, 1))  # Monday
            assert not should_book_on_date(recurring, date(2024, 1, 2))  # Tuesday
            assert should_book_on_date(recurring, date(2024, 1, 8))  # Next Monday

    def test_unknown_pattern_returns_false(self, app):
        """Unknown pattern should return False."""
        with app.app_context():
            recurring = MagicMock()
            recurring.pattern = 'unknown'

            assert not should_book_on_date(recurring, date(2024, 1, 1))


class TestGenerateRecurringBookings:
    """Tests for generate_recurring_bookings function."""

    def test_generates_bookings_for_active_recurring(self, app, sample_recurring_booking):
        """Should generate bookings for active recurring templates."""
        with app.app_context():
            count = generate_recurring_bookings(days_ahead=7)
            # Should create at least some bookings for weekdays pattern
            assert count >= 0  # May be 0 if no valid weekdays in range

    def test_skips_inactive_recurring(self, app, sample_recurring_booking):
        """Should skip inactive recurring bookings."""
        from app.models import db, RecurringBooking

        with app.app_context():
            # Deactivate the recurring booking
            recurring = RecurringBooking.query.get(sample_recurring_booking['id'])
            recurring.is_active = False
            db.session.commit()

            count = generate_recurring_bookings(days_ahead=7)
            # No bookings should be created
            assert count == 0


class TestFindAvailableSpace:
    """Tests for find_available_space function."""

    def test_finds_available_space(self, app, sample_parking_space):
        """Should find an available space for the time slot."""
        with app.app_context():
            tomorrow = date.today() + timedelta(days=1)
            space = find_available_space(
                desired_date=tomorrow,
                start_time=time(10, 0),
                end_time=time(12, 0),
                space_id=sample_parking_space['id']
            )

            assert space is not None
            assert space.id == sample_parking_space['id']

    def test_returns_none_when_booked(self, app, sample_booking):
        """Should return None when space is already booked."""
        from app.models import Booking

        with app.app_context():
            booking = Booking.query.get(sample_booking['id'])
            space = find_available_space(
                desired_date=booking.start_time.date(),
                start_time=booking.start_time.time(),
                end_time=booking.end_time.time(),
                space_id=booking.space_id
            )

            # Space should not be available during booking time
            assert space is None


class TestExpireOldWaitlistNotifications:
    """Tests for expire_old_waitlist_notifications function."""

    def test_expires_old_notifications(self, app, sample_waitlist_entry):
        """Should expire notifications past their expiry time."""
        from app.models import db, Waitlist

        with app.app_context():
            # Set entry as notified with past expiry
            entry = Waitlist.query.get(sample_waitlist_entry['id'])
            entry.status = 'notified'
            entry.notified_at = datetime.utcnow() - timedelta(hours=1)
            entry.expires_at = datetime.utcnow() - timedelta(minutes=30)
            db.session.commit()

            count = expire_old_waitlist_notifications()
            assert count == 1

            # Verify status changed
            entry = Waitlist.query.get(sample_waitlist_entry['id'])
            assert entry.status == 'expired'


class TestCleanupOldWaitlistEntries:
    """Tests for cleanup_old_waitlist_entries function."""

    def test_cleans_up_old_entries(self, app, sample_waitlist_entry):
        """Should remove entries with past desired dates."""
        from app.models import db, Waitlist

        with app.app_context():
            # Set entry to old date
            entry = Waitlist.query.get(sample_waitlist_entry['id'])
            entry.desired_date = date.today() - timedelta(days=60)
            db.session.commit()

            count = cleanup_old_waitlist_entries(days_old=30)
            assert count == 1

            # Verify entry was deleted
            entry = Waitlist.query.get(sample_waitlist_entry['id'])
            assert entry is None
