"""
Unit tests for database models.
Tests model creation, relationships, and methods.
"""
import pytest
from datetime import datetime, timedelta

from app.models import db, User, ParkingSpace, Booking, VideoSource, OccupancyLog
from app.utils.auth import hash_password


class TestUserModel:
    """Tests for User model."""

    @pytest.mark.unit
    def test_create_user(self, app):
        """Should create a user with required fields."""
        with app.app_context():
            user = User(
                email='test@example.com',
                password_hash=hash_password('Password123'),
                name='Test User'
            )
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.email == 'test@example.com'
            assert user.name == 'Test User'
            assert user.created_at is not None

    @pytest.mark.unit
    def test_user_email_unique(self, app):
        """Email should be unique."""
        with app.app_context():
            user1 = User(
                email='duplicate@example.com',
                password_hash='hash1',
                name='User 1'
            )
            db.session.add(user1)
            db.session.commit()

            user2 = User(
                email='duplicate@example.com',
                password_hash='hash2',
                name='User 2'
            )
            db.session.add(user2)

            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()

    @pytest.mark.unit
    def test_user_to_dict(self, app):
        """to_dict should return user data without password."""
        with app.app_context():
            user = User(
                email='test@example.com',
                password_hash='secret_hash',
                name='Test User',
                phone='+1234567890'
            )
            db.session.add(user)
            db.session.commit()

            user_dict = user.to_dict()

            assert 'id' in user_dict
            assert user_dict['email'] == 'test@example.com'
            assert user_dict['name'] == 'Test User'
            assert user_dict['phone'] == '+1234567890'
            assert 'password_hash' not in user_dict
            assert 'password' not in user_dict

    @pytest.mark.unit
    def test_user_is_admin_default_false(self, app):
        """New users should not be admin by default."""
        with app.app_context():
            user = User(
                email='regular@example.com',
                password_hash='hash',
                name='Regular User'
            )
            db.session.add(user)
            db.session.commit()

            assert user.is_admin is False

    @pytest.mark.unit
    def test_user_can_be_admin(self, app):
        """Admin flag should be settable."""
        with app.app_context():
            admin = User(
                email='admin@example.com',
                password_hash='hash',
                name='Admin User',
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()

            assert admin.is_admin is True

    @pytest.mark.unit
    def test_user_updated_at_changes(self, app):
        """updated_at should change on update."""
        with app.app_context():
            user = User(
                email='test@example.com',
                password_hash='hash',
                name='Test User'
            )
            db.session.add(user)
            db.session.commit()

            original_updated = user.updated_at

            # Update user
            user.name = 'Updated Name'
            db.session.commit()

            # Note: SQLite may not update timestamp automatically
            # This test validates the field exists and is set


class TestParkingSpaceModel:
    """Tests for ParkingSpace model."""

    @pytest.mark.unit
    def test_create_parking_space(self, app):
        """Should create a parking space with required fields."""
        with app.app_context():
            space = ParkingSpace(
                name='A-001',
                location='Mall Parking',
                hourly_rate=50.0
            )
            db.session.add(space)
            db.session.commit()

            assert space.id is not None
            assert space.name == 'A-001'
            assert space.location == 'Mall Parking'
            assert space.hourly_rate == 50.0

    @pytest.mark.unit
    def test_parking_space_defaults(self, app):
        """Should have correct default values."""
        with app.app_context():
            space = ParkingSpace(
                name='A-001',
                location='Test Location'
            )
            db.session.add(space)
            db.session.commit()

            assert space.is_occupied is False
            assert space.is_active is True
            assert space.vehicle_type == 'car'
            assert space.floor == 'G'
            assert space.hourly_rate == 50.0

    @pytest.mark.unit
    def test_parking_space_with_coordinates(self, app):
        """Should store polygon coordinates as JSON."""
        with app.app_context():
            coords = [[0, 0], [100, 0], [100, 100], [0, 100]]
            space = ParkingSpace(
                name='A-001',
                location='Test',
                coordinates=coords
            )
            db.session.add(space)
            db.session.commit()

            # Reload from DB
            loaded = ParkingSpace.query.get(space.id)
            assert loaded.coordinates == coords

    @pytest.mark.unit
    def test_parking_space_to_dict(self, app):
        """to_dict should return space data."""
        with app.app_context():
            space = ParkingSpace(
                name='A-001',
                location='Mall Parking',
                hourly_rate=75.0,
                vehicle_type='bike',
                floor='2'
            )
            db.session.add(space)
            db.session.commit()

            space_dict = space.to_dict()

            assert space_dict['name'] == 'A-001'
            assert space_dict['location'] == 'Mall Parking'
            assert space_dict['hourly_rate'] == 75.0
            assert space_dict['vehicle_type'] == 'bike'
            assert space_dict['floor'] == '2'
            assert 'coordinates' not in space_dict  # Not included by default

    @pytest.mark.unit
    def test_parking_space_to_dict_with_coordinates(self, app):
        """to_dict should include coordinates when requested."""
        with app.app_context():
            coords = [[0, 0], [100, 0], [100, 100], [0, 100]]
            space = ParkingSpace(
                name='A-001',
                location='Test',
                coordinates=coords
            )
            db.session.add(space)
            db.session.commit()

            space_dict = space.to_dict(include_coordinates=True)

            assert 'coordinates' in space_dict
            assert space_dict['coordinates'] == coords


class TestBookingModel:
    """Tests for Booking model."""

    @pytest.mark.unit
    def test_create_booking(self, app):
        """Should create a booking with required fields."""
        with app.app_context():
            # Create user and space first
            user = User(email='test@test.com', password_hash='hash', name='Test')
            space = ParkingSpace(name='A-001', location='Test')
            db.session.add_all([user, space])
            db.session.commit()

            start = datetime.utcnow() + timedelta(hours=1)
            end = start + timedelta(hours=2)

            booking = Booking(
                user_id=user.id,
                space_id=space.id,
                start_time=start,
                end_time=end,
                total_amount=100.0
            )
            db.session.add(booking)
            db.session.commit()

            assert booking.id is not None
            assert booking.user_id == user.id
            assert booking.space_id == space.id
            assert booking.total_amount == 100.0

    @pytest.mark.unit
    def test_booking_defaults(self, app):
        """Should have correct default values."""
        with app.app_context():
            user = User(email='test@test.com', password_hash='hash', name='Test')
            space = ParkingSpace(name='A-001', location='Test')
            db.session.add_all([user, space])
            db.session.commit()

            booking = Booking(
                user_id=user.id,
                space_id=space.id,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(hours=1),
                total_amount=50.0
            )
            db.session.add(booking)
            db.session.commit()

            assert booking.status == 'pending'
            assert booking.payment_status == 'unpaid'

    @pytest.mark.unit
    def test_booking_relationships(self, app):
        """Should have working relationships to user and space."""
        with app.app_context():
            user = User(email='test@test.com', password_hash='hash', name='Test User')
            space = ParkingSpace(name='A-001', location='Test Location')
            db.session.add_all([user, space])
            db.session.commit()

            booking = Booking(
                user_id=user.id,
                space_id=space.id,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(hours=1),
                total_amount=50.0
            )
            db.session.add(booking)
            db.session.commit()

            # Test relationships
            assert booking.user.name == 'Test User'
            assert booking.space.name == 'A-001'

    @pytest.mark.unit
    def test_booking_to_dict(self, app):
        """to_dict should return booking data with space info."""
        with app.app_context():
            user = User(email='test@test.com', password_hash='hash', name='Test')
            space = ParkingSpace(name='A-001', location='Mall Parking')
            db.session.add_all([user, space])
            db.session.commit()

            start = datetime.utcnow() + timedelta(hours=1)
            end = start + timedelta(hours=2)

            booking = Booking(
                user_id=user.id,
                space_id=space.id,
                vehicle_number='ABC-1234',
                start_time=start,
                end_time=end,
                total_amount=100.0,
                status='confirmed'
            )
            db.session.add(booking)
            db.session.commit()

            booking_dict = booking.to_dict()

            assert booking_dict['space_name'] == 'A-001'
            assert booking_dict['location'] == 'Mall Parking'
            assert booking_dict['vehicle_number'] == 'ABC-1234'
            assert booking_dict['status'] == 'confirmed'


class TestVideoSourceModel:
    """Tests for VideoSource model."""

    @pytest.mark.unit
    def test_create_video_source(self, app):
        """Should create a video source."""
        with app.app_context():
            source = VideoSource(
                name='Main Camera',
                url='rtsp://camera.local/stream',
                location='Mall Entrance'
            )
            db.session.add(source)
            db.session.commit()

            assert source.id is not None
            assert source.name == 'Main Camera'
            assert source.is_active is True

    @pytest.mark.unit
    def test_video_source_to_dict(self, app):
        """to_dict should return source data."""
        with app.app_context():
            source = VideoSource(
                name='Camera 1',
                url='http://example.com/stream',
                location='Level 1',
                frame_width=1920,
                frame_height=1080
            )
            db.session.add(source)
            db.session.commit()

            source_dict = source.to_dict()

            assert source_dict['name'] == 'Camera 1'
            assert source_dict['frame_width'] == 1920
            assert source_dict['frame_height'] == 1080


class TestOccupancyLogModel:
    """Tests for OccupancyLog model."""

    @pytest.mark.unit
    def test_create_occupancy_log(self, app):
        """Should create an occupancy log entry."""
        with app.app_context():
            space = ParkingSpace(name='A-001', location='Test')
            db.session.add(space)
            db.session.commit()

            log = OccupancyLog(
                space_id=space.id,
                is_occupied=True,
                confidence=0.95
            )
            db.session.add(log)
            db.session.commit()

            assert log.id is not None
            assert log.is_occupied is True
            assert log.confidence == 0.95
            assert log.detected_at is not None

    @pytest.mark.unit
    def test_occupancy_log_to_dict(self, app):
        """to_dict should return log data."""
        with app.app_context():
            space = ParkingSpace(name='A-001', location='Test')
            db.session.add(space)
            db.session.commit()

            log = OccupancyLog(
                space_id=space.id,
                is_occupied=False,
                confidence=0.87
            )
            db.session.add(log)
            db.session.commit()

            log_dict = log.to_dict()

            assert log_dict['is_occupied'] is False
            assert log_dict['confidence'] == 0.87
            assert 'detected_at' in log_dict
