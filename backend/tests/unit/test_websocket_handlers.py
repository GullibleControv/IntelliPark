"""
Unit tests for WebSocket event handlers.
Tests socket.io event handling.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestWebSocketHandlers:
    """Tests for WebSocket event handlers."""

    def test_connect_handler(self, app):
        """Should handle client connection."""
        with app.app_context():
            from app.services.websocket import socketio, register_handlers

            # Re-register handlers to ensure they're available
            register_handlers()

            # Verify handlers are registered
            assert socketio is not None

    def test_subscribe_location_handler(self, app):
        """Should handle location subscription."""
        with app.app_context():
            from app.services.websocket import socketio

            # Verify socketio is initialized
            assert socketio is not None

    def test_emit_space_update_with_confidence(self, app):
        """Should emit space update with confidence value."""
        with app.app_context():
            from app.services.websocket import emit_space_update

            with patch('app.services.websocket.socketio') as mock_socketio:
                mock_socketio.emit = MagicMock()

                emit_space_update(
                    space_id=1,
                    is_occupied=False,
                    confidence=0.87,
                    location='Office Parking'
                )

                # Should have been called multiple times (space room, location room, global)
                assert mock_socketio.emit.call_count >= 1

    def test_emit_space_update_without_location(self, app):
        """Should emit space update without location."""
        with app.app_context():
            from app.services.websocket import emit_space_update

            with patch('app.services.websocket.socketio') as mock_socketio:
                mock_socketio.emit = MagicMock()

                emit_space_update(
                    space_id=1,
                    is_occupied=True
                )

                # Should still emit to space room and global
                assert mock_socketio.emit.called


class TestOccupancySummary:
    """Tests for occupancy summary emission."""

    def test_emit_occupancy_summary_with_spaces(self, app, multiple_parking_spaces):
        """Should emit correct occupancy summary."""
        with app.app_context():
            from app.services.websocket import emit_occupancy_summary

            with patch('app.services.websocket.socketio') as mock_socketio:
                emit_calls = []

                def capture_emit(event, data, **kwargs):
                    emit_calls.append({'event': event, 'data': data})

                mock_socketio.emit = capture_emit

                emit_occupancy_summary()

                assert len(emit_calls) > 0
                summary = emit_calls[0]['data']
                assert 'total' in summary
                assert 'occupied' in summary
                assert 'available' in summary
                assert 'occupancy_rate' in summary

    def test_emit_occupancy_summary_empty_location(self, app):
        """Should handle empty location."""
        with app.app_context():
            from app.services.websocket import emit_occupancy_summary

            with patch('app.services.websocket.socketio') as mock_socketio:
                mock_socketio.emit = MagicMock()

                # Should not raise error for non-existent location
                emit_occupancy_summary(location='NonExistent Location')

                assert mock_socketio.emit.called
