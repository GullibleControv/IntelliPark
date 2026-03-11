"""
Admin routes for parking space configuration and detection management.
"""

from flask import Blueprint, request, jsonify
import subprocess
import base64
import logging

from app.models import db, ParkingSpace, VideoSource
from app.utils.auth import token_required

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/extract-frame', methods=['POST'])
@token_required
def extract_frame():
    """
    Extract a frame from a YouTube video URL.
    Uses yt-dlp to get stream URL, then OpenCV to capture frame.
    Returns the frame as a base64 encoded JPEG.
    """
    try:
        import cv2
    except ImportError:
        return jsonify({'error': 'OpenCV not installed. Run: pip install opencv-python'}), 500

    data = request.get_json()
    youtube_url = data.get('url')

    if not youtube_url:
        return jsonify({'error': 'YouTube URL is required'}), 400

    try:
        # Use yt-dlp to get the direct video stream URL
        result = subprocess.run(
            ['yt-dlp', '-f', 'best[height<=720]', '-g', youtube_url],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"yt-dlp error: {result.stderr}")
            return jsonify({'error': 'Failed to extract video URL. Check if the URL is valid.'}), 400

        stream_url = result.stdout.strip()

        if not stream_url:
            return jsonify({'error': 'Could not get stream URL'}), 400

        # Capture a frame using OpenCV
        cap = cv2.VideoCapture(stream_url)

        if not cap.isOpened():
            return jsonify({'error': 'Failed to open video stream'}), 400

        # Skip ahead a few seconds for a better frame
        cap.set(cv2.CAP_PROP_POS_MSEC, 5000)

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return jsonify({'error': 'Failed to capture frame from video'}), 400

        # Get frame dimensions
        height, width = frame.shape[:2]

        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame_base64 = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            'frame': f'data:image/jpeg;base64,{frame_base64}',
            'width': width,
            'height': height
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Video extraction timed out. Try a different URL.'}), 408
    except FileNotFoundError:
        return jsonify({'error': 'yt-dlp not installed. Run: pip install yt-dlp'}), 500
    except Exception as e:
        logger.error(f"Frame extraction error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/video-sources', methods=['POST'])
@token_required
def create_video_source():
    """Create a new video source configuration."""
    data = request.get_json()

    if not data or not data.get('url') or not data.get('name'):
        return jsonify({'error': 'URL and name are required'}), 400

    source = VideoSource(
        name=data['name'],
        url=data['url'],
        location=data.get('location', 'Default Location'),
        frame_width=data.get('frame_width'),
        frame_height=data.get('frame_height'),
        is_active=True
    )

    db.session.add(source)
    db.session.commit()

    return jsonify({
        'message': 'Video source created',
        'source': source.to_dict()
    }), 201


@admin_bp.route('/video-sources', methods=['GET'])
@token_required
def get_video_sources():
    """Get all video sources."""
    sources = VideoSource.query.filter_by(is_active=True).all()
    return jsonify({
        'sources': [s.to_dict() for s in sources]
    })


@admin_bp.route('/video-sources/<int:source_id>', methods=['DELETE'])
@token_required
def delete_video_source(source_id):
    """Delete a video source."""
    source = VideoSource.query.get_or_404(source_id)
    source.is_active = False
    db.session.commit()
    return jsonify({'message': 'Video source deleted'})


@admin_bp.route('/spaces-with-coordinates', methods=['GET'])
@token_required
def get_spaces_with_coordinates():
    """Get all parking spaces with their coordinates for editing."""
    location = request.args.get('location')

    query = ParkingSpace.query.filter_by(is_active=True)
    if location:
        query = query.filter_by(location=location)

    spaces = query.all()

    return jsonify({
        'spaces': [s.to_dict(include_coordinates=True) for s in spaces]
    })


@admin_bp.route('/spaces/bulk', methods=['POST'])
@token_required
def create_bulk_spaces():
    """Create multiple parking spaces at once (from polygon drawing session)."""
    data = request.get_json()

    if not data or not data.get('spaces'):
        return jsonify({'error': 'Spaces array is required'}), 400

    location = data.get('location', 'Default Location')
    created_spaces = []

    for space_data in data['spaces']:
        coordinates = space_data.get('coordinates', [])

        if len(coordinates) < 3:
            continue  # Skip invalid polygons

        space = ParkingSpace(
            name=space_data.get('name', f'Space {len(created_spaces) + 1}'),
            location=location,
            coordinates=coordinates,
            hourly_rate=space_data.get('hourly_rate', 50.0),
            vehicle_type=space_data.get('vehicle_type', 'car'),
            floor=space_data.get('floor', 'G')
        )

        db.session.add(space)
        created_spaces.append(space)

    db.session.commit()

    return jsonify({
        'message': f'Created {len(created_spaces)} parking spaces',
        'spaces': [s.to_dict(include_coordinates=True) for s in created_spaces]
    }), 201


@admin_bp.route('/detection/config', methods=['GET'])
@token_required
def get_detection_config():
    """Get detection configuration for a video source."""
    source_id = request.args.get('source_id', type=int)

    if not source_id:
        return jsonify({'error': 'Video source ID is required'}), 400

    source = VideoSource.query.get_or_404(source_id)

    # Get spaces for this location
    spaces = ParkingSpace.query.filter_by(
        location=source.location,
        is_active=True
    ).all()

    return jsonify({
        'source': source.to_dict(),
        'spaces_count': len(spaces),
        'command': f'python detector.py --source "{source.url}" --config config.yaml'
    })
