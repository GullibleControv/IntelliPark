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
