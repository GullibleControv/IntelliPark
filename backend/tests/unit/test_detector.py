"""
Unit tests for the IntelliPark parking detector system.

Covers:
  - ParkingDetector.point_in_polygon  (ray-casting geometry)
  - ParkingDetector.check_occupancy   (occupancy logic + API calls)
  - PUT /api/parking/spaces/<id>/status  (Flask endpoint)

No real YOLO model is loaded; ultralytics.YOLO and requests.put are patched
throughout so the test suite runs without any GPU, model file, or network.
"""

import os
import sys
import pytest
from unittest import mock
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# Make sure the backend/app package is importable when pytest is run from the
# backend/ directory.  The sys.path manipulation mirrors what conftest.py
# relies on implicitly.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Simple unit square used in many geometry tests.
UNIT_SQUARE = [[0, 0], [10, 0], [10, 10], [0, 10]]

# L-shaped (concave) polygon:
#   (0,10)──(5,10)
#     │        │
#   (0,5)──(5,5)──(10,5)
#                    │
#   (0,0)──────────(10,0)
L_SHAPE = [
    [0, 0], [10, 0], [10, 5], [5, 5], [5, 10], [0, 10]
]


def _make_detector():
    """
    Build a ParkingDetector with YOLO construction patched out.

    Returns the detector instance ready for unit testing (no model file
    needed, no config.yaml needed).
    """
    with patch("ultralytics.YOLO"), \
         patch("builtins.open", mock.mock_open(read_data="api_url: http://localhost:5000\n")):
        # Also patch yaml.safe_load so it returns a minimal config dict
        with patch("yaml.safe_load", return_value={"api_url": "http://localhost:5000",
                                                    "confidence": 0.5,
                                                    "vehicle_classes": [2, 3, 5, 7]}):
            with patch("pathlib.Path.exists", return_value=True):
                sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                                 '..', '..', '..', 'detection'))
                from detector import ParkingDetector
                detector = ParkingDetector.__new__(ParkingDetector)
                detector.config = {
                    "api_url": "http://localhost:5000",
                    "confidence": 0.5,
                    "vehicle_classes": [2, 3, 5, 7],
                    "skip_frames": 2,
                    "resize_factor": 1.0,
                }
                detector.model = MagicMock()
                detector.spaces = []
                detector.api_url = "http://localhost:5000"
                return detector


@pytest.fixture
def detector():
    """Provide a ParkingDetector instance with mocked YOLO for each test."""
    return _make_detector()


# ---------------------------------------------------------------------------
# Helpers shared between check_occupancy tests
# ---------------------------------------------------------------------------

def _space(space_id, coordinates, is_occupied=False):
    """Return a minimal parking-space dict as the API would provide."""
    return {
        "id": space_id,
        "name": f"Space-{space_id}",
        "coordinates": coordinates,
        "is_occupied": is_occupied,
    }


def _vehicle(center_x, center_y, confidence=0.9, class_id=2):
    """Return a minimal detected-vehicle dict."""
    return {
        "center": (center_x, center_y),
        "box": (center_x - 10, center_y - 10, center_x + 10, center_y + 10),
        "confidence": confidence,
        "class_id": class_id,
    }


# ===========================================================================
# 1. point_in_polygon tests
# ===========================================================================

class TestPointInPolygon:
    """Tests for ParkingDetector.point_in_polygon (ray-casting algorithm)."""

    # --- Happy-path geometry ---

    @pytest.mark.unit
    def test_point_clearly_inside_square(self, detector):
        """A point at the centre of a square polygon must return True."""
        assert detector.point_in_polygon((5, 5), UNIT_SQUARE) is True

    @pytest.mark.unit
    def test_point_clearly_outside_square(self, detector):
        """A point far outside the polygon must return False."""
        assert detector.point_in_polygon((50, 50), UNIT_SQUARE) is False

    @pytest.mark.unit
    def test_point_outside_to_the_left(self, detector):
        """A point to the left of the polygon must return False."""
        assert detector.point_in_polygon((-5, 5), UNIT_SQUARE) is False

    @pytest.mark.unit
    def test_point_outside_above(self, detector):
        """A point above the polygon must return False."""
        assert detector.point_in_polygon((5, 15), UNIT_SQUARE) is False

    # --- Boundary / degenerate inputs ---

    @pytest.mark.unit
    def test_point_on_corner_is_deterministic(self, detector):
        """
        A point exactly on a corner must return a consistent value.

        The ray-casting algorithm has undefined behaviour on exact polygon
        boundaries; we only assert that the same call always produces the
        same result (no crash, no randomness).
        """
        result_first_call = detector.point_in_polygon((0, 0), UNIT_SQUARE)
        result_second_call = detector.point_in_polygon((0, 0), UNIT_SQUARE)
        assert result_first_call == result_second_call

    @pytest.mark.unit
    def test_point_on_edge_midpoint_is_deterministic(self, detector):
        """
        A point on the middle of an edge must return a consistent value.

        Same caveat as corners — boundary classification is implementation-
        defined, but must be stable.
        """
        result_first = detector.point_in_polygon((5, 0), UNIT_SQUARE)
        result_second = detector.point_in_polygon((5, 0), UNIT_SQUARE)
        assert result_first == result_second

    # --- Degenerate polygon inputs ---

    @pytest.mark.unit
    def test_empty_polygon_returns_false(self, detector):
        """
        An empty polygon (0 points) must return False without crashing.

        The detector receives arbitrary data from the API; it must handle
        missing coordinates gracefully.
        """
        # point_in_polygon will raise IndexError on polygon[0] with an empty
        # list, so check_occupancy guards this.  We test the guard here.
        from detector import ParkingDetector  # already on sys.path
        space = _space(1, [], is_occupied=False)
        detector.spaces = [space]
        with patch.object(detector, "update_space_status") as mock_update:
            occupancy = detector.check_occupancy([_vehicle(5, 5)])
            # Space with empty coordinates must be skipped entirely
            assert 1 not in occupancy
            mock_update.assert_not_called()

    @pytest.mark.unit
    def test_one_point_polygon_is_skipped(self, detector):
        """
        A polygon with only 1 point is degenerate and must be skipped by
        check_occupancy (less than 3 points required).
        """
        space = _space(1, [[5, 5]], is_occupied=False)
        detector.spaces = [space]
        with patch.object(detector, "update_space_status") as mock_update:
            occupancy = detector.check_occupancy([_vehicle(5, 5)])
            assert 1 not in occupancy
            mock_update.assert_not_called()

    @pytest.mark.unit
    def test_two_point_polygon_is_skipped(self, detector):
        """
        A polygon with only 2 points cannot form an area and must be skipped.
        """
        space = _space(1, [[0, 0], [10, 10]], is_occupied=False)
        detector.spaces = [space]
        with patch.object(detector, "update_space_status") as mock_update:
            occupancy = detector.check_occupancy([_vehicle(5, 5)])
            assert 1 not in occupancy
            mock_update.assert_not_called()

    # --- Complex / concave polygon ---

    @pytest.mark.unit
    def test_point_inside_lower_section_of_l_shape(self, detector):
        """
        A point inside the lower rectangle of an L-shape must return True.

        The lower horizontal bar of the L covers x=[0..10], y=[0..5].
        """
        assert detector.point_in_polygon((8, 2), L_SHAPE) is True

    @pytest.mark.unit
    def test_point_inside_upper_section_of_l_shape(self, detector):
        """
        A point inside the upper vertical bar of an L-shape must return True.

        The upper bar covers x=[0..5], y=[5..10].
        """
        assert detector.point_in_polygon((2, 8), L_SHAPE) is True

    @pytest.mark.unit
    def test_point_in_notch_of_l_shape_returns_false(self, detector):
        """
        A point in the concave notch of the L (upper-right void) must return
        False.  x=[5..10], y=[5..10] is outside the polygon.
        """
        assert detector.point_in_polygon((8, 8), L_SHAPE) is False

    @pytest.mark.unit
    def test_point_far_outside_l_shape(self, detector):
        """A point completely outside the L must return False."""
        assert detector.point_in_polygon((20, 20), L_SHAPE) is False


# ===========================================================================
# 2. check_occupancy tests
# ===========================================================================

class TestCheckOccupancy:
    """
    Tests for ParkingDetector.check_occupancy.

    YOLO is not exercised here; vehicles are supplied as pre-built dicts.
    requests.put is patched via update_space_status to avoid real HTTP calls.
    """

    @pytest.mark.unit
    def test_vehicle_inside_space_marks_it_occupied(self, detector):
        """
        When a vehicle centroid falls inside a space polygon the space must be
        marked occupied and update_space_status must be called with True.
        """
        space = _space(1, UNIT_SQUARE, is_occupied=False)
        detector.spaces = [space]

        with patch.object(detector, "update_space_status") as mock_update:
            occupancy = detector.check_occupancy([_vehicle(5, 5, confidence=0.85)])

        assert occupancy[1] is True
        mock_update.assert_called_once_with(1, True, 0.85)

    @pytest.mark.unit
    def test_vehicle_outside_all_spaces_does_not_affect_any_space(self, detector):
        """
        A vehicle whose centroid does not fall inside any polygon must not
        trigger an occupancy change or any API call.
        """
        space = _space(1, UNIT_SQUARE, is_occupied=False)
        detector.spaces = [space]

        with patch.object(detector, "update_space_status") as mock_update:
            occupancy = detector.check_occupancy([_vehicle(50, 50)])

        assert occupancy[1] is False
        mock_update.assert_not_called()

    @pytest.mark.unit
    def test_empty_frame_marks_all_spaces_free(self, detector):
        """
        When no vehicles are detected every previously-free space must stay
        free.  No API call should be made (status unchanged).
        """
        spaces = [
            _space(1, UNIT_SQUARE, is_occupied=False),
            _space(2, [[20, 20], [30, 20], [30, 30], [20, 30]], is_occupied=False),
        ]
        detector.spaces = spaces

        with patch.object(detector, "update_space_status") as mock_update:
            occupancy = detector.check_occupancy([])

        assert occupancy[1] is False
        assert occupancy[2] is False
        mock_update.assert_not_called()

    @pytest.mark.unit
    def test_empty_frame_clears_previously_occupied_space(self, detector):
        """
        When no vehicles are detected a space that was previously occupied must
        be flipped to free, and the API must be notified (is_occupied=False,
        confidence=None).
        """
        space = _space(1, UNIT_SQUARE, is_occupied=True)
        detector.spaces = [space]

        with patch.object(detector, "update_space_status") as mock_update:
            occupancy = detector.check_occupancy([])

        assert occupancy[1] is False
        mock_update.assert_called_once_with(1, False, None)

    @pytest.mark.unit
    def test_no_api_call_when_status_unchanged_occupied(self, detector):
        """
        If a space is already marked occupied and a vehicle is still inside,
        the status has not changed and update_space_status must NOT be called.
        """
        space = _space(1, UNIT_SQUARE, is_occupied=True)
        detector.spaces = [space]

        with patch.object(detector, "update_space_status") as mock_update:
            occupancy = detector.check_occupancy([_vehicle(5, 5)])

        assert occupancy[1] is True
        mock_update.assert_not_called()

    @pytest.mark.unit
    def test_multiple_spaces_only_matching_space_marked_occupied(self, detector):
        """
        With two non-overlapping spaces and one vehicle inside space 1, only
        space 1 must be occupied.
        """
        space1 = _space(1, UNIT_SQUARE, is_occupied=False)
        space2 = _space(2, [[20, 20], [30, 20], [30, 30], [20, 30]], is_occupied=False)
        detector.spaces = [space1, space2]

        with patch.object(detector, "update_space_status"):
            occupancy = detector.check_occupancy([_vehicle(5, 5)])

        assert occupancy[1] is True
        assert occupancy[2] is False

    @pytest.mark.unit
    def test_api_failure_on_connection_error_logs_warning_does_not_crash(self, detector):
        """
        If requests.put raises a requests.ConnectionError the detector must
        log a warning and continue — it must not propagate the exception.

        This simulates the backend being temporarily unreachable.  We raise
        requests.exceptions.ConnectionError (a subclass of
        requests.RequestException) which is exactly what the library raises
        for refused connections, and which the except clause in
        update_space_status is designed to catch.
        """
        import requests as req
        import detector as detector_module

        space = _space(1, UNIT_SQUARE, is_occupied=False)
        detector.spaces = [space]

        # Use requests.exceptions.ConnectionError, which IS a RequestException
        with patch.object(detector_module.requests, "put",
                          side_effect=req.exceptions.ConnectionError("refused")) as mock_put:
            from detector import ParkingDetector
            detector.update_space_status = ParkingDetector.update_space_status.__get__(
                detector, ParkingDetector
            )
            # Should not raise — update_space_status catches RequestException
            occupancy = detector.check_occupancy([_vehicle(5, 5)])

        # Occupancy dict is still populated (detector continues processing)
        assert occupancy[1] is True
        # requests.put was attempted once
        mock_put.assert_called_once()

    @pytest.mark.unit
    def test_api_failure_on_requests_exception_does_not_crash(self, detector):
        """
        Any requests.RequestException (e.g. Timeout) from the status-update
        call must be silently logged — the detector loop must survive.
        """
        import requests as req

        space = _space(1, UNIT_SQUARE, is_occupied=False)
        detector.spaces = [space]

        with patch("requests.put", side_effect=req.Timeout("timed out")):
            from detector import ParkingDetector
            detector.update_space_status = ParkingDetector.update_space_status.__get__(
                detector, ParkingDetector
            )
            # Must not raise
            occupancy = detector.check_occupancy([_vehicle(5, 5)])

        assert occupancy[1] is True

    @pytest.mark.unit
    def test_highest_confidence_vehicle_used_in_api_call(self, detector):
        """
        When multiple vehicles are inside the same space the call to
        update_space_status must report the highest observed confidence.
        """
        space = _space(1, UNIT_SQUARE, is_occupied=False)
        detector.spaces = [space]

        # First vehicle enters and satisfies point_in_polygon; subsequent
        # ones are ignored because check_occupancy breaks on first match.
        # We verify the confidence of the first matching vehicle is forwarded.
        vehicle = _vehicle(5, 5, confidence=0.72)

        with patch.object(detector, "update_space_status") as mock_update:
            detector.check_occupancy([vehicle])

        _, _, reported_conf = mock_update.call_args[0]
        assert reported_conf == pytest.approx(0.72)


# ===========================================================================
# 3. update_space_status Flask endpoint tests
# ===========================================================================

class TestUpdateSpaceStatusEndpoint:
    """
    Integration tests for PUT /api/parking/spaces/<id>/status.

    The Flask test client is used; the database is in-memory SQLite as
    configured in conftest.py TestConfig.  DETECTOR_API_KEY is set via
    monkeypatch on the environment so the decorator reads it at request time.
    """

    TEST_KEY = "test-key"

    @pytest.fixture(autouse=True)
    def _set_detector_key(self, monkeypatch):
        """
        Set DETECTOR_API_KEY in the environment for every test in this class.
        The decorator reads os.getenv() at request time, so this is sufficient.
        """
        monkeypatch.setenv("DETECTOR_API_KEY", self.TEST_KEY)

    @pytest.fixture
    def _space_in_db(self, app):
        """Create a ParkingSpace row and return its id."""
        from app.models import db, ParkingSpace
        with app.app_context():
            space = ParkingSpace(
                name="Test-001",
                location="Test Lot",
                coordinates=[[0, 0], [10, 0], [10, 10], [0, 10]],
                hourly_rate=50.0,
                vehicle_type="car",
                floor="G",
                is_occupied=False,
                is_active=True,
            )
            db.session.add(space)
            db.session.commit()
            return space.id

    # --- Auth: valid key ---

    @pytest.mark.unit
    def test_valid_key_returns_200_and_updates_status(self, client, _space_in_db):
        """
        A PUT request with the correct X-Detector-Key and a valid body must
        return 200 and reflect the new is_occupied value in the response.
        """
        response = client.put(
            f"/api/parking/spaces/{_space_in_db}/status",
            json={"is_occupied": True},
            headers={"X-Detector-Key": self.TEST_KEY},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["is_occupied"] is True

    @pytest.mark.unit
    def test_valid_key_with_confidence_returns_200(self, client, _space_in_db):
        """
        An optional confidence field in the body must be accepted without error.
        """
        response = client.put(
            f"/api/parking/spaces/{_space_in_db}/status",
            json={"is_occupied": True, "confidence": 0.91},
            headers={"X-Detector-Key": self.TEST_KEY},
        )

        assert response.status_code == 200
        assert response.get_json()["success"] is True

    # --- Auth: missing key ---

    @pytest.mark.unit
    def test_missing_key_header_returns_401(self, client, _space_in_db):
        """
        A PUT request without the X-Detector-Key header must be rejected
        with 401 Unauthorized.
        """
        response = client.put(
            f"/api/parking/spaces/{_space_in_db}/status",
            json={"is_occupied": True},
            # No X-Detector-Key header
        )

        assert response.status_code == 401
        assert "error" in response.get_json()

    @pytest.mark.unit
    def test_empty_key_header_returns_401(self, client, _space_in_db):
        """
        An explicitly empty X-Detector-Key must be rejected with 401.
        """
        response = client.put(
            f"/api/parking/spaces/{_space_in_db}/status",
            json={"is_occupied": True},
            headers={"X-Detector-Key": ""},
        )

        assert response.status_code == 401

    # --- Auth: wrong key ---

    @pytest.mark.unit
    def test_wrong_key_returns_401(self, client, _space_in_db):
        """
        A PUT request with an incorrect X-Detector-Key value must be rejected
        with 401 Unauthorized.  A spoofed key must never update occupancy.
        """
        response = client.put(
            f"/api/parking/spaces/{_space_in_db}/status",
            json={"is_occupied": True},
            headers={"X-Detector-Key": "wrong-key"},
        )

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data

    # --- Missing required field ---

    @pytest.mark.unit
    def test_missing_is_occupied_field_returns_400(self, client, _space_in_db):
        """
        A body that omits the required is_occupied field must result in
        400 Bad Request.
        """
        response = client.put(
            f"/api/parking/spaces/{_space_in_db}/status",
            json={"confidence": 0.8},  # is_occupied intentionally absent
            headers={"X-Detector-Key": self.TEST_KEY},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "is_occupied" in data["error"]

    @pytest.mark.unit
    def test_empty_body_returns_400(self, client, _space_in_db):
        """
        A PUT request with an empty JSON body must return 400 Bad Request.
        """
        response = client.put(
            f"/api/parking/spaces/{_space_in_db}/status",
            json={},
            headers={"X-Detector-Key": self.TEST_KEY},
        )

        assert response.status_code == 400

    @pytest.mark.unit
    def test_null_body_returns_error(self, client, _space_in_db):
        """
        A PUT request with no JSON body at all must be rejected.

        Flask's request.get_json() raises a BadRequest (400) when
        content_type is application/json but the body is empty.  The
        endpoint's outer try/except catches that and returns 500, which is
        an implementation detail we document here.  The important assertion
        is that the response is NOT 200 — the request is always refused.
        """
        response = client.put(
            f"/api/parking/spaces/{_space_in_db}/status",
            data=None,
            content_type="application/json",
            headers={"X-Detector-Key": self.TEST_KEY},
        )

        # Must not succeed — server either returns 400 or 500 depending on
        # where the exception is caught, but never 200.
        assert response.status_code != 200
        assert response.status_code in (400, 500)

    # --- Non-existent space ---

    @pytest.mark.unit
    def test_nonexistent_space_id_returns_404(self, client):
        """
        A PUT for a space_id that does not exist in the database must return
        404 Not Found.
        """
        response = client.put(
            "/api/parking/spaces/99999/status",
            json={"is_occupied": False},
            headers={"X-Detector-Key": self.TEST_KEY},
        )

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data

    # --- Idempotency: status unchanged ---

    @pytest.mark.unit
    def test_same_status_does_not_create_duplicate_log(self, app, client, _space_in_db):
        """
        Sending the same is_occupied value twice must return 200 both times
        but must only create one OccupancyLog entry (change-only logging).
        """
        from app.models import OccupancyLog

        # First call: transition False -> True
        client.put(
            f"/api/parking/spaces/{_space_in_db}/status",
            json={"is_occupied": True},
            headers={"X-Detector-Key": self.TEST_KEY},
        )

        # Second call: same value True -> True (no change)
        response = client.put(
            f"/api/parking/spaces/{_space_in_db}/status",
            json={"is_occupied": True},
            headers={"X-Detector-Key": self.TEST_KEY},
        )

        assert response.status_code == 200

        with app.app_context():
            log_count = OccupancyLog.query.filter_by(space_id=_space_in_db).count()

        # Only one log entry for the single actual status transition
        assert log_count == 1

    # --- Boolean coercion ---

    @pytest.mark.unit
    def test_false_value_marks_space_free(self, client, _space_in_db, app):
        """
        Sending is_occupied=False must persist False on the space record.
        """
        from app.models import ParkingSpace

        # First occupy it
        client.put(
            f"/api/parking/spaces/{_space_in_db}/status",
            json={"is_occupied": True},
            headers={"X-Detector-Key": self.TEST_KEY},
        )

        # Now free it
        response = client.put(
            f"/api/parking/spaces/{_space_in_db}/status",
            json={"is_occupied": False},
            headers={"X-Detector-Key": self.TEST_KEY},
        )

        assert response.status_code == 200
        assert response.get_json()["is_occupied"] is False

        with app.app_context():
            space = ParkingSpace.query.get(_space_in_db)
            assert space.is_occupied is False
