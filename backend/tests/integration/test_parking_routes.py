"""
Integration tests for parking space routes.
Tests the full request/response cycle for parking endpoints.
"""
import pytest

from app.models import db, ParkingSpace


class TestGetSpaces:
    """Tests for GET /api/parking/spaces"""

    @pytest.mark.integration
    def test_get_spaces_empty(self, client):
        """Should return empty list when no spaces exist."""
        response = client.get('/api/parking/spaces')

        assert response.status_code == 200
        data = response.get_json()
        assert data['spaces'] == []
        assert data['total'] == 0

    @pytest.mark.integration
    def test_get_spaces_with_data(self, client, multiple_parking_spaces):
        """Should return all active parking spaces."""
        response = client.get('/api/parking/spaces')

        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 5

    @pytest.mark.integration
    def test_get_spaces_filter_by_location(self, client, multiple_parking_spaces):
        """Should filter spaces by location."""
        response = client.get('/api/parking/spaces?location=Mall')

        assert response.status_code == 200
        data = response.get_json()
        # 3 spaces are at "Mall Parking"
        assert data['total'] == 3
        for space in data['spaces']:
            assert 'Mall' in space['location']

    @pytest.mark.integration
    def test_get_spaces_filter_available(self, client, multiple_parking_spaces):
        """Should filter only available spaces."""
        response = client.get('/api/parking/spaces?available=true')

        assert response.status_code == 200
        data = response.get_json()
        for space in data['spaces']:
            assert space['is_occupied'] is False

    @pytest.mark.integration
    def test_get_spaces_filter_by_vehicle_type(self, client, multiple_parking_spaces):
        """Should filter by vehicle type."""
        response = client.get('/api/parking/spaces?vehicle_type=bike')

        assert response.status_code == 200
        data = response.get_json()
        for space in data['spaces']:
            assert space['vehicle_type'] == 'bike'

    @pytest.mark.integration
    def test_get_spaces_filter_by_floor(self, client, multiple_parking_spaces):
        """Should filter by floor."""
        response = client.get('/api/parking/spaces?floor=0')

        assert response.status_code == 200
        data = response.get_json()
        for space in data['spaces']:
            assert space['floor'] == '0'


class TestGetSingleSpace:
    """Tests for GET /api/parking/spaces/<id>"""

    @pytest.mark.integration
    def test_get_space_success(self, client, sample_parking_space):
        """Should return a single space with coordinates."""
        response = client.get(f'/api/parking/spaces/{sample_parking_space["id"]}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['space']['name'] == 'A-001'
        assert 'coordinates' in data['space']

    @pytest.mark.integration
    def test_get_space_not_found(self, client):
        """Should return 404 for non-existent space."""
        response = client.get('/api/parking/spaces/99999')

        assert response.status_code == 404


class TestCreateSpace:
    """Tests for POST /api/parking/spaces (admin only)"""

    @pytest.mark.integration
    def test_create_space_success(self, client, admin_headers):
        """Should create a new parking space (admin only)."""
        response = client.post('/api/parking/spaces', headers=admin_headers, json={
            'name': 'B-001',
            'location': 'New Parking Area',
            'hourly_rate': 75.0,
            'vehicle_type': 'car',
            'floor': '2'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['space']['name'] == 'B-001'
        assert data['space']['hourly_rate'] == 75.0

    @pytest.mark.integration
    def test_create_space_with_coordinates(self, client, admin_headers):
        """Should create space with polygon coordinates (admin only)."""
        coords = [[0, 0], [50, 0], [50, 50], [0, 50]]
        response = client.post('/api/parking/spaces', headers=admin_headers, json={
            'name': 'C-001',
            'location': 'Test Area',
            'coordinates': coords
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['space']['coordinates'] == coords

    @pytest.mark.integration
    def test_create_space_missing_fields(self, client, admin_headers):
        """Should fail with missing required fields."""
        response = client.post('/api/parking/spaces', headers=admin_headers, json={
            'name': 'Test'
        })

        assert response.status_code == 400

    @pytest.mark.integration
    def test_create_space_no_auth(self, client):
        """Should fail without authentication."""
        response = client.post('/api/parking/spaces', json={
            'name': 'Test',
            'location': 'Test'
        })

        assert response.status_code == 401

    @pytest.mark.integration
    def test_create_space_non_admin_forbidden(self, client, auth_headers):
        """Should fail for non-admin users."""
        response = client.post('/api/parking/spaces', headers=auth_headers, json={
            'name': 'Test',
            'location': 'Test'
        })

        assert response.status_code == 403

    @pytest.mark.integration
    def test_create_space_invalid_coordinates(self, client, admin_headers):
        """Should fail with less than 3 coordinate points."""
        response = client.post('/api/parking/spaces', headers=admin_headers, json={
            'name': 'Test',
            'location': 'Test',
            'coordinates': [[0, 0], [100, 0]]  # Only 2 points
        })

        assert response.status_code == 400


class TestUpdateSpace:
    """Tests for PUT /api/parking/spaces/<id>"""

    @pytest.mark.integration
    def test_update_space_success(self, client, admin_headers, sample_parking_space):
        """Should update parking space (admin only)."""
        response = client.put(
            f'/api/parking/spaces/{sample_parking_space["id"]}',
            headers=admin_headers,
            json={'name': 'A-001-Updated', 'hourly_rate': 100.0}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['space']['name'] == 'A-001-Updated'
        assert data['space']['hourly_rate'] == 100.0

    @pytest.mark.integration
    def test_update_space_not_found(self, client, admin_headers):
        """Should return 404 for non-existent space."""
        response = client.put(
            '/api/parking/spaces/99999',
            headers=admin_headers,
            json={'name': 'Test'}
        )

        assert response.status_code == 404


class TestDeleteSpace:
    """Tests for DELETE /api/parking/spaces/<id>"""

    @pytest.mark.integration
    def test_delete_space_soft_delete(self, client, app, admin_headers, sample_parking_space):
        """Should soft delete (deactivate) space (admin only)."""
        response = client.delete(
            f'/api/parking/spaces/{sample_parking_space["id"]}',
            headers=admin_headers
        )

        assert response.status_code == 200

        # Verify soft delete
        with app.app_context():
            space = ParkingSpace.query.get(sample_parking_space['id'])
            assert space.is_active is False


class TestUpdateSpaceStatus:
    """Tests for PUT /api/parking/spaces/<id>/status"""

    @pytest.mark.integration
    def test_update_status_success(self, client, sample_parking_space):
        """Should update occupancy status."""
        response = client.put(
            f'/api/parking/spaces/{sample_parking_space["id"]}/status',
            json={'is_occupied': True, 'confidence': 0.95}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['is_occupied'] is True

    @pytest.mark.integration
    def test_update_status_creates_log(self, client, app, sample_parking_space):
        """Should create occupancy log when status changes."""
        from app.models import OccupancyLog

        response = client.put(
            f'/api/parking/spaces/{sample_parking_space["id"]}/status',
            json={'is_occupied': True}
        )

        assert response.status_code == 200

        with app.app_context():
            logs = OccupancyLog.query.filter_by(
                space_id=sample_parking_space['id']
            ).all()
            assert len(logs) == 1
            assert logs[0].is_occupied is True

    @pytest.mark.integration
    def test_update_status_no_log_when_same(self, client, app, sample_parking_space):
        """Should not create log when status unchanged."""
        from app.models import OccupancyLog

        # Space starts as not occupied, send same status
        response = client.put(
            f'/api/parking/spaces/{sample_parking_space["id"]}/status',
            json={'is_occupied': False}
        )

        assert response.status_code == 200

        with app.app_context():
            logs = OccupancyLog.query.filter_by(
                space_id=sample_parking_space['id']
            ).all()
            assert len(logs) == 0

    @pytest.mark.integration
    def test_update_status_missing_field(self, client, sample_parking_space):
        """Should fail without is_occupied field."""
        response = client.put(
            f'/api/parking/spaces/{sample_parking_space["id"]}/status',
            json={'confidence': 0.95}
        )

        assert response.status_code == 400


class TestOverallStatus:
    """Tests for GET /api/parking/status"""

    @pytest.mark.integration
    def test_overall_status_empty(self, client):
        """Should return zeros when no spaces exist."""
        response = client.get('/api/parking/status')

        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 0
        assert data['available'] == 0
        assert data['occupied'] == 0

    @pytest.mark.integration
    def test_overall_status_with_data(self, client, multiple_parking_spaces):
        """Should return correct summary."""
        response = client.get('/api/parking/status')

        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 5
        # Spaces 0, 2, 4 are occupied (i % 2 == 0)
        assert data['occupied'] == 3
        assert data['available'] == 2

    @pytest.mark.integration
    def test_overall_status_with_location_filter(self, client, multiple_parking_spaces):
        """Should filter by location."""
        response = client.get('/api/parking/status?location=Office')

        assert response.status_code == 200
        data = response.get_json()
        # Only 2 spaces at "Office Parking"
        assert data['total'] == 2


class TestGetLocations:
    """Tests for GET /api/parking/locations"""

    @pytest.mark.integration
    def test_get_locations(self, client, multiple_parking_spaces):
        """Should return unique locations."""
        response = client.get('/api/parking/locations')

        assert response.status_code == 200
        data = response.get_json()
        assert 'Mall Parking' in data['locations']
        assert 'Office Parking' in data['locations']
        assert len(data['locations']) == 2
