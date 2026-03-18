"""
WebSocket service for real-time parking updates.
Provides real-time notifications for parking space status changes.
"""
import logging
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request

logger = logging.getLogger(__name__)

# Initialize SocketIO without app (will be initialized in create_app)
socketio = SocketIO()


def init_socketio(app):
    """Initialize SocketIO with the Flask app."""
    # Determine async mode - try eventlet first, fall back to threading
    async_mode = 'threading'
    if not app.config.get('TESTING'):
        try:
            import eventlet
            async_mode = 'eventlet'
        except ImportError:
            try:
                import gevent
                async_mode = 'gevent'
            except ImportError:
                async_mode = 'threading'

    socketio.init_app(
        app,
        cors_allowed_origins=app.config.get('CORS_ORIGINS', '*'),
        async_mode=async_mode,
        logger=False,
        engineio_logger=False
    )
    register_handlers()
    logger.info("WebSocket service initialized")
    return socketio


def register_handlers():
    """Register WebSocket event handlers."""

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        logger.debug(f"Client connected: {request.sid}")
        emit('connected', {'status': 'connected', 'sid': request.sid})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        logger.debug(f"Client disconnected: {request.sid}")

    @socketio.on('subscribe_location')
    def handle_subscribe_location(data):
        """
        Subscribe to updates for a specific parking location.
        Clients in a room receive updates only for that location.
        """
        location = data.get('location')
        if location:
            join_room(f"location_{location}")
            logger.debug(f"Client {request.sid} subscribed to location: {location}")
            emit('subscribed', {'location': location, 'status': 'subscribed'})

    @socketio.on('unsubscribe_location')
    def handle_unsubscribe_location(data):
        """Unsubscribe from a parking location."""
        location = data.get('location')
        if location:
            leave_room(f"location_{location}")
            logger.debug(f"Client {request.sid} unsubscribed from location: {location}")
            emit('unsubscribed', {'location': location, 'status': 'unsubscribed'})

    @socketio.on('subscribe_space')
    def handle_subscribe_space(data):
        """Subscribe to updates for a specific parking space."""
        space_id = data.get('space_id')
        if space_id:
            join_room(f"space_{space_id}")
            logger.debug(f"Client {request.sid} subscribed to space: {space_id}")
            emit('subscribed', {'space_id': space_id, 'status': 'subscribed'})

    @socketio.on('ping')
    def handle_ping():
        """Handle ping for connection health check."""
        emit('pong', {'status': 'alive'})


def emit_space_update(space_id, is_occupied, confidence=None, location=None):
    """
    Emit a parking space status update to all subscribed clients.

    Args:
        space_id: The parking space ID
        is_occupied: Whether the space is now occupied
        confidence: Detection confidence (0-1)
        location: The parking location name
    """
    from datetime import datetime

    update_data = {
        'space_id': space_id,
        'is_occupied': is_occupied,
        'confidence': confidence,
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': 'space_update'
    }

    # Emit to space-specific room
    socketio.emit('space_update', update_data, room=f"space_{space_id}")

    # Emit to location room if location provided
    if location:
        update_data['location'] = location
        socketio.emit('space_update', update_data, room=f"location_{location}")

    # Emit to global room for dashboard
    socketio.emit('space_update', update_data)

    logger.debug(f"Emitted space update: space_id={space_id}, occupied={is_occupied}")


def emit_booking_update(user_id, booking_data, event_type='booking_update'):
    """
    Emit a booking update to a specific user.

    Args:
        user_id: The user to notify
        booking_data: The booking information
        event_type: Type of booking event (created, cancelled, started, completed)
    """
    from datetime import datetime

    update_data = {
        'booking': booking_data,
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat()
    }

    socketio.emit('booking_update', update_data, room=f"user_{user_id}")
    logger.debug(f"Emitted booking update to user {user_id}: {event_type}")


def emit_occupancy_summary(location=None):
    """
    Emit overall occupancy summary.
    Called periodically or when significant changes occur.
    """
    from app.models import ParkingSpace

    query = ParkingSpace.query.filter_by(is_active=True)
    if location:
        query = query.filter_by(location=location)

    spaces = query.all()
    total = len(spaces)
    occupied = sum(1 for s in spaces if s.is_occupied)

    summary = {
        'total': total,
        'occupied': occupied,
        'available': total - occupied,
        'occupancy_rate': round((occupied / total * 100), 1) if total > 0 else 0,
        'event_type': 'occupancy_summary'
    }

    if location:
        summary['location'] = location
        socketio.emit('occupancy_summary', summary, room=f"location_{location}")
    else:
        socketio.emit('occupancy_summary', summary)

    logger.debug(f"Emitted occupancy summary: {summary}")
