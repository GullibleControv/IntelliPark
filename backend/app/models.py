from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    """User model for authentication and profile."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bookings = db.relationship('Booking', backref='user', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'phone': self.phone,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ParkingSpace(db.Model):
    """Parking space model for tracking individual spots."""

    __tablename__ = 'parking_spaces'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False, index=True)
    coordinates = db.Column(db.JSON, nullable=True)  # Polygon points for detection
    is_occupied = db.Column(db.Boolean, default=False, index=True)
    hourly_rate = db.Column(db.Float, default=50.0)
    vehicle_type = db.Column(db.String(20), default='car')  # car, bike, truck
    floor = db.Column(db.String(10), default='G')  # Ground, 1, 2, etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bookings = db.relationship('Booking', backref='space', lazy=True, cascade='all, delete-orphan')

    def to_dict(self, include_coordinates=False):
        data = {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'is_occupied': self.is_occupied,
            'hourly_rate': self.hourly_rate,
            'vehicle_type': self.vehicle_type,
            'floor': self.floor,
            'is_active': self.is_active
        }
        if include_coordinates:
            data['coordinates'] = self.coordinates
        return data


class Booking(db.Model):
    """Booking model for parking reservations."""

    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    space_id = db.Column(db.Integer, db.ForeignKey('parking_spaces.id'), nullable=False, index=True)
    vehicle_number = db.Column(db.String(20), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending', index=True)  # pending, confirmed, active, completed, cancelled
    payment_status = db.Column(db.String(20), default='unpaid')  # unpaid, paid, refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'space_id': self.space_id,
            'space_name': self.space.name if self.space else None,
            'location': self.space.location if self.space else None,
            'vehicle_number': self.vehicle_number,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_amount': self.total_amount,
            'status': self.status,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class VideoSource(db.Model):
    """Video source configuration for detection system."""

    __tablename__ = 'video_sources'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    frame_width = db.Column(db.Integer, nullable=True)
    frame_height = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'location': self.location,
            'frame_width': self.frame_width,
            'frame_height': self.frame_height,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class OccupancyLog(db.Model):
    """Log of occupancy changes for analytics."""

    __tablename__ = 'occupancy_logs'

    id = db.Column(db.Integer, primary_key=True)
    space_id = db.Column(db.Integer, db.ForeignKey('parking_spaces.id'), nullable=False, index=True)
    is_occupied = db.Column(db.Boolean, nullable=False)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    confidence = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'space_id': self.space_id,
            'is_occupied': self.is_occupied,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'confidence': self.confidence
        }


class RecurringBooking(db.Model):
    """Recurring booking template for repeated parking reservations."""

    __tablename__ = 'recurring_bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    space_id = db.Column(db.Integer, db.ForeignKey('parking_spaces.id'), nullable=False, index=True)
    pattern = db.Column(db.String(20), nullable=False)  # daily, weekly, weekdays, weekends
    start_time = db.Column(db.Time, nullable=False)  # Time of day to start
    end_time = db.Column(db.Time, nullable=False)  # Time of day to end
    days_of_week = db.Column(db.JSON, nullable=True)  # [0-6] for specific days (0=Monday)
    valid_from = db.Column(db.Date, nullable=False)
    valid_until = db.Column(db.Date, nullable=True)  # None = indefinite
    is_active = db.Column(db.Boolean, default=True)
    vehicle_number = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='recurring_bookings')
    space = db.relationship('ParkingSpace', backref='recurring_bookings')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'space_id': self.space_id,
            'space_name': self.space.name if self.space else None,
            'location': self.space.location if self.space else None,
            'pattern': self.pattern,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'days_of_week': self.days_of_week,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'is_active': self.is_active,
            'vehicle_number': self.vehicle_number,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Waitlist(db.Model):
    """Waitlist for parking spaces when fully booked."""

    __tablename__ = 'waitlists'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    space_id = db.Column(db.Integer, db.ForeignKey('parking_spaces.id'), nullable=True)
    location = db.Column(db.String(100), nullable=True)  # Can wait for any space at location
    desired_date = db.Column(db.Date, nullable=False, index=True)
    desired_start_time = db.Column(db.Time, nullable=False)
    desired_end_time = db.Column(db.Time, nullable=False)
    vehicle_type = db.Column(db.String(20), default='car')
    status = db.Column(db.String(20), default='waiting', index=True)  # waiting, notified, booked, expired
    notified_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)  # Notification expiry
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='waitlist_entries')
    space = db.relationship('ParkingSpace', backref='waitlist_entries')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'space_id': self.space_id,
            'space_name': self.space.name if self.space else None,
            'location': self.location or (self.space.location if self.space else None),
            'desired_date': self.desired_date.isoformat() if self.desired_date else None,
            'desired_start_time': self.desired_start_time.isoformat() if self.desired_start_time else None,
            'desired_end_time': self.desired_end_time.isoformat() if self.desired_end_time else None,
            'vehicle_type': self.vehicle_type,
            'status': self.status,
            'notified_at': self.notified_at.isoformat() if self.notified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
