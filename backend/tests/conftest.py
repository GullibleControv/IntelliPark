"""
Pytest fixtures and configuration for IntelliPark tests.
"""
import pytest
from datetime import datetime, timedelta

from app import create_app
from app.models import db, User, ParkingSpace, Booking, VideoSource, OccupancyLog, RecurringBooking, Waitlist
from app.utils.auth import hash_password, generate_token
from app.config import Config


class TestConfig(Config):
    """Test configuration using in-memory SQLite."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key-for-testing-only'
    JWT_EXPIRATION_HOURS = 1
    WTF_CSRF_ENABLED = False


@pytest.fixture(scope='function')
def app():
    """Create application for testing."""
    application = create_app(TestConfig)

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Provide database session for tests."""
    with app.app_context():
        yield db.session


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing."""
    with app.app_context():
        user = User(
            email='test@example.com',
            password_hash=hash_password('TestPass123'),
            name='Test User',
            phone='+1234567890'
        )
        db.session.add(user)
        db.session.commit()

        # Refresh to get ID
        db.session.refresh(user)
        user_dict = user.to_dict()
        user_dict['id'] = user.id
        return user_dict


@pytest.fixture
def sample_admin(app):
    """Create a sample admin user for testing."""
    with app.app_context():
        admin = User(
            email='admin@example.com',
            password_hash=hash_password('AdminPass123'),
            name='Admin User',
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

        db.session.refresh(admin)
        admin_dict = admin.to_dict()
        admin_dict['id'] = admin.id
        return admin_dict


@pytest.fixture
def auth_token(app, sample_user):
    """Generate auth token for sample user."""
    with app.app_context():
        return generate_token(sample_user['id'])


@pytest.fixture
def admin_token(app, sample_admin):
    """Generate auth token for admin user."""
    with app.app_context():
        return generate_token(sample_admin['id'])


@pytest.fixture
def auth_headers(auth_token):
    """Return authorization headers with token."""
    return {'Authorization': f'Bearer {auth_token}'}


@pytest.fixture
def admin_headers(admin_token):
    """Return authorization headers with admin token."""
    return {'Authorization': f'Bearer {admin_token}'}


@pytest.fixture
def sample_parking_space(app):
    """Create a sample parking space for testing."""
    with app.app_context():
        space = ParkingSpace(
            name='A-001',
            location='Mall Parking - Level 1',
            coordinates=[[0, 0], [100, 0], [100, 100], [0, 100]],
            hourly_rate=50.0,
            vehicle_type='car',
            floor='1',
            is_occupied=False,
            is_active=True
        )
        db.session.add(space)
        db.session.commit()

        db.session.refresh(space)
        space_dict = space.to_dict(include_coordinates=True)
        space_dict['id'] = space.id
        return space_dict


@pytest.fixture
def sample_booking(app, sample_user, sample_parking_space):
    """Create a sample booking for testing."""
    with app.app_context():
        # Need to get user and space from DB
        user = User.query.get(sample_user['id'])
        space = ParkingSpace.query.get(sample_parking_space['id'])

        start_time = datetime.utcnow() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        booking = Booking(
            user_id=user.id,
            space_id=space.id,
            vehicle_number='ABC-1234',
            start_time=start_time,
            end_time=end_time,
            total_amount=100.0,
            status='confirmed',
            payment_status='unpaid'
        )
        db.session.add(booking)
        db.session.commit()

        db.session.refresh(booking)
        booking_dict = booking.to_dict()
        booking_dict['id'] = booking.id
        return booking_dict


@pytest.fixture
def multiple_parking_spaces(app):
    """Create multiple parking spaces for testing."""
    with app.app_context():
        spaces = []
        for i in range(5):
            space = ParkingSpace(
                name=f'A-{i+1:03d}',
                location='Mall Parking' if i < 3 else 'Office Parking',
                hourly_rate=50.0 + (i * 10),
                vehicle_type='car' if i % 2 == 0 else 'bike',
                floor=str(i // 2),
                is_occupied=i % 2 == 0,
                is_active=True
            )
            db.session.add(space)
            spaces.append(space)

        db.session.commit()

        return [{'id': s.id, **s.to_dict()} for s in spaces]


@pytest.fixture
def sample_recurring_booking(app, sample_user, sample_parking_space):
    """Create a sample recurring booking for testing."""
    from datetime import date, time
    with app.app_context():
        recurring = RecurringBooking(
            user_id=sample_user['id'],
            space_id=sample_parking_space['id'],
            pattern='weekdays',
            start_time=time(9, 0),
            end_time=time(17, 0),
            valid_from=date.today(),
            is_active=True
        )
        db.session.add(recurring)
        db.session.commit()

        db.session.refresh(recurring)
        return {'id': recurring.id, **recurring.to_dict()}


@pytest.fixture
def sample_waitlist_entry(app, sample_user, sample_parking_space):
    """Create a sample waitlist entry for testing."""
    from datetime import date, time, timedelta
    with app.app_context():
        entry = Waitlist(
            user_id=sample_user['id'],
            space_id=sample_parking_space['id'],
            desired_date=date.today() + timedelta(days=1),
            desired_start_time=time(10, 0),
            desired_end_time=time(12, 0),
            status='waiting'
        )
        db.session.add(entry)
        db.session.commit()

        db.session.refresh(entry)
        return {'id': entry.id, **entry.to_dict()}
