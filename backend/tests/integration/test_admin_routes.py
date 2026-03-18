"""
Integration tests for admin routes.
Tests the full request/response cycle for admin endpoints.
"""
import pytest

from app.models import db, VideoSource, ParkingSpace


class TestExtractFrame:
    """Tests for POST /api/admin/extract-frame"""

    @pytest.mark.integration
    def test_extract_frame_no_url(self, client, admin_headers):
        """Should fail without YouTube URL."""
        response = client.post('/api/admin/extract-frame', headers=admin_headers, json={})

        assert response.status_code == 400
        assert 'required' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_extract_frame_no_auth(self, client):
        """Should fail without authentication."""
        response = client.post('/api/admin/extract-frame', json={
            'url': 'https://youtube.com/watch?v=test'
        })

        assert response.status_code == 401


class TestVideoSources:
    """Tests for video source CRUD operations."""

    @pytest.mark.integration
    def test_create_video_source_success(self, client, admin_headers):
        """Should create a new video source."""
        response = client.post('/api/admin/video-sources', headers=admin_headers, json={
            'name': 'Test Camera',
            'url': 'rtsp://camera.local/stream',
            'location': 'Parking Level 1',
            'frame_width': 1920,
            'frame_height': 1080
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['source']['name'] == 'Test Camera'
        assert data['source']['url'] == 'rtsp://camera.local/stream'

    @pytest.mark.integration
    def test_create_video_source_missing_fields(self, client, admin_headers):
        """Should fail with missing required fields."""
        response = client.post('/api/admin/video-sources', headers=admin_headers, json={
            'name': 'Test Camera'
            # Missing 'url'
        })

        assert response.status_code == 400

    @pytest.mark.integration
    def test_create_video_source_default_location(self, client, admin_headers):
        """Should use default location if not provided."""
        response = client.post('/api/admin/video-sources', headers=admin_headers, json={
            'name': 'Default Camera',
            'url': 'rtsp://camera.local/stream'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['source']['location'] == 'Default Location'

    @pytest.mark.integration
    def test_get_video_sources_empty(self, client, admin_headers):
        """Should return empty list when no sources exist."""
        response = client.get('/api/admin/video-sources', headers=admin_headers)

        assert response.status_code == 200
        assert response.get_json()['sources'] == []

    @pytest.mark.integration
    def test_get_video_sources_with_data(self, client, app, admin_headers):
        """Should return all active video sources."""
        # Create a source
        with app.app_context():
            source = VideoSource(
                name='Test Camera',
                url='http://test.com/stream',
                location='Test'
            )
            db.session.add(source)
            db.session.commit()

        response = client.get('/api/admin/video-sources', headers=admin_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['sources']) == 1

    @pytest.mark.integration
    def test_delete_video_source(self, client, app, admin_headers):
        """Should soft delete a video source."""
        # Create a source
        with app.app_context():
            source = VideoSource(
                name='To Delete',
                url='http://test.com/stream',
                location='Test'
            )
            db.session.add(source)
            db.session.commit()
            source_id = source.id

        response = client.delete(
            f'/api/admin/video-sources/{source_id}',
            headers=admin_headers
        )

        assert response.status_code == 200

        # Verify soft delete
        with app.app_context():
            source = VideoSource.query.get(source_id)
            assert source.is_active is False


class TestSpacesWithCoordinates:
    """Tests for GET /api/admin/spaces-with-coordinates"""

    @pytest.mark.integration
    def test_get_spaces_with_coordinates(self, client, admin_headers, sample_parking_space):
        """Should return spaces with coordinates."""
        response = client.get(
            '/api/admin/spaces-with-coordinates',
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['spaces']) >= 1
        # Verify coordinates are included
        for space in data['spaces']:
            assert 'coordinates' in space

    @pytest.mark.integration
    def test_get_spaces_filter_by_location(self, client, app, admin_headers):
        """Should filter spaces by location."""
        with app.app_context():
            space1 = ParkingSpace(name='A-001', location='Mall Parking')
            space2 = ParkingSpace(name='B-001', location='Office Parking')
            db.session.add_all([space1, space2])
            db.session.commit()

        response = client.get(
            '/api/admin/spaces-with-coordinates?location=Mall Parking',
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        for space in data['spaces']:
            assert space['location'] == 'Mall Parking'


class TestBulkSpaces:
    """Tests for POST /api/admin/spaces/bulk"""

    @pytest.mark.integration
    def test_create_bulk_spaces_success(self, client, admin_headers):
        """Should create multiple parking spaces."""
        response = client.post('/api/admin/spaces/bulk', headers=admin_headers, json={
            'location': 'New Parking Lot',
            'spaces': [
                {
                    'name': 'A-001',
                    'coordinates': [[0, 0], [100, 0], [100, 100], [0, 100]],
                    'hourly_rate': 50.0
                },
                {
                    'name': 'A-002',
                    'coordinates': [[100, 0], [200, 0], [200, 100], [100, 100]],
                    'hourly_rate': 60.0
                }
            ]
        })

        assert response.status_code == 201
        data = response.get_json()
        assert 'Created 2' in data['message']
        assert len(data['spaces']) == 2

    @pytest.mark.integration
    def test_create_bulk_spaces_empty(self, client, admin_headers):
        """Should fail with empty spaces array."""
        response = client.post('/api/admin/spaces/bulk', headers=admin_headers, json={})

        assert response.status_code == 400

    @pytest.mark.integration
    def test_create_bulk_spaces_skip_invalid(self, client, admin_headers):
        """Should skip spaces with invalid coordinates."""
        response = client.post('/api/admin/spaces/bulk', headers=admin_headers, json={
            'location': 'Test',
            'spaces': [
                {
                    'name': 'Valid',
                    'coordinates': [[0, 0], [100, 0], [100, 100], [0, 100]]
                },
                {
                    'name': 'Invalid',
                    'coordinates': [[0, 0], [100, 0]]  # Only 2 points
                }
            ]
        })

        assert response.status_code == 201
        data = response.get_json()
        # Only 1 should be created (invalid skipped)
        assert len(data['spaces']) == 1
        assert data['spaces'][0]['name'] == 'Valid'


class TestDetectionConfig:
    """Tests for GET /api/admin/detection/config"""

    @pytest.mark.integration
    def test_get_detection_config_no_source_id(self, client, admin_headers):
        """Should fail without source_id parameter."""
        response = client.get(
            '/api/admin/detection/config',
            headers=admin_headers
        )

        assert response.status_code == 400
        assert 'required' in response.get_json()['error'].lower()

    @pytest.mark.integration
    def test_get_detection_config_success(self, client, app, admin_headers):
        """Should return detection config with space count."""
        with app.app_context():
            source = VideoSource(
                name='Camera 1',
                url='rtsp://camera/stream',
                location='Mall Parking'
            )
            space = ParkingSpace(name='A-001', location='Mall Parking')
            db.session.add_all([source, space])
            db.session.commit()
            source_id = source.id

        response = client.get(
            f'/api/admin/detection/config?source_id={source_id}',
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['spaces_count'] >= 1
        assert 'command' in data
