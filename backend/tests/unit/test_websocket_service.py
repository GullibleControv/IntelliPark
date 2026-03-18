"""
Unit tests for WebSocket service.
Tests real-time event emission.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestWebSocketService:
    """Tests for WebSocket service functions."""

    def test_emit_space_update(self, app):
        """Should emit space update event."""
        with app.app_context():
            from app.services.websocket import emit_space_update

            with patch('app.services.websocket.socketio') as mock_socketio:
                mock_socketio.emit = MagicMock()

                emit_space_update(
                    space_id=1,
                    is_occupied=True,
                    location='Mall Parking'
                )

                # Verify emit was called
                assert mock_socketio.emit.called

    def test_emit_booking_update(self, app):
        """Should emit booking update event."""
        with app.app_context():
            from app.services.websocket import emit_booking_update

            with patch('app.services.websocket.socketio') as mock_socketio:
                mock_socketio.emit = MagicMock()

                emit_booking_update(
                    user_id=1,
                    booking_data={'id': 1, 'status': 'confirmed'},
                    event_type='booking_created'
                )

                assert mock_socketio.emit.called

    def test_emit_occupancy_summary(self, app, sample_parking_space):
        """Should emit occupancy summary event."""
        with app.app_context():
            from app.services.websocket import emit_occupancy_summary

            with patch('app.services.websocket.socketio') as mock_socketio:
                mock_socketio.emit = MagicMock()

                # Call with location parameter (function queries database)
                emit_occupancy_summary(location='Mall Parking - Level 1')

                # Verify emit was called
                assert mock_socketio.emit.called

    def test_emit_occupancy_summary_all_locations(self, app, sample_parking_space):
        """Should emit occupancy summary for all locations."""
        with app.app_context():
            from app.services.websocket import emit_occupancy_summary

            with patch('app.services.websocket.socketio') as mock_socketio:
                mock_socketio.emit = MagicMock()

                # Call without location (all locations)
                emit_occupancy_summary()

                assert mock_socketio.emit.called


class TestSocketIOInit:
    """Tests for SocketIO initialization."""

    def test_init_socketio(self, app):
        """Should initialize SocketIO without errors."""
        with app.app_context():
            from app.services.websocket import init_socketio

            # Should not raise an error
            init_socketio(app)


class TestEmitSpaceUpdateData:
    """Tests for space update data structure."""

    def test_emit_space_update_data_format(self, app):
        """Should emit data in correct format."""
        with app.app_context():
            from app.services.websocket import emit_space_update

            with patch('app.services.websocket.socketio') as mock_socketio:
                emit_calls = []

                def capture_emit(event, data, **kwargs):
                    emit_calls.append({'event': event, 'data': data, 'kwargs': kwargs})

                mock_socketio.emit = capture_emit

                emit_space_update(
                    space_id=1,
                    is_occupied=True,
                    confidence=0.95,
                    location='Mall Parking'
                )

                # Verify data structure
                assert len(emit_calls) > 0
                call = emit_calls[0]
                assert call['event'] == 'space_update'
                assert call['data']['space_id'] == 1
                assert call['data']['is_occupied'] is True
                assert call['data']['confidence'] == 0.95
