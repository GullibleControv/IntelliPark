"""
Admin routes for parking space configuration and detection management.
"""

from flask import Blueprint, request, jsonify
import base64
import logging
import re
from urllib.parse import urlparse
import yt_dlp

from app.models import db, ParkingSpace, VideoSource
from app.utils.auth import admin_required
from app.routes.parking import validate_coordinates

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def validate_youtube_url(url: str) -> bool:
    """
    Validate that a URL is a legitimate YouTube URL.
    Prevents command injection by strictly validating URL format.
    """
    if not url or not isinstance(url, str):
        return False

    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # Whitelist YouTube domains
    allowed_hosts = [
        'youtube.com',
        'www.youtube.com',
        'm.youtube.com',
        'youtu.be',
        'www.youtu.be'
    ]

    if parsed.netloc not in allowed_hosts:
        return False

    # Must be HTTPS
    if parsed.scheme not in ['http', 'https']:
        return False

    # Check for shell metacharacters (defense in depth)
    dangerous_chars = [';', '|', '&', '$', '`', '(', ')', '{', '}', '<', '>', '\n', '\r']
    if any(char in url for char in dangerous_chars):
        return False

    # Validate video ID pattern for youtube.com/watch?v=
    if 'youtube.com' in parsed.netloc:
        video_id_pattern = r'^[a-zA-Z0-9_-]{11}$'
        # Extract video ID from query params
        from urllib.parse import parse_qs
        query_params = parse_qs(parsed.query)
        video_id = query_params.get('v', [None])[0]
        if video_id and not re.match(video_id_pattern, video_id):
            return False

    # Validate youtu.be short URL format
    if 'youtu.be' in parsed.netloc:
        video_id_pattern = r'^/[a-zA-Z0-9_-]{11}$'
        if not re.match(video_id_pattern, parsed.path):
            return False

    return True


def extract_video_url(youtube_url: str) -> str:
    """
    Extract the direct video stream URL from a YouTube URL using yt-dlp Python API.

    Args:
        youtube_url: Validated YouTube URL

    Returns:
        Direct video stream URL

    Raises:
        Exception: If video extraction fails
    """
    ydl_opts = {
        'format': 'best[height<=720]',
        'quiet': True,
        'no_warnings': True,
        'no_color': True,
        'socket_timeout': 60
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        if not info or 'url' not in info:
            raise ValueError('Could not extract video URL')
        return info['url']


@admin_bp.route('/extract-frame', methods=['POST'])
@admin_required
def extract_frame():
    """
    Extract a frame from a YouTube video URL.
    Uses yt-dlp to get stream URL, then OpenCV to capture frame.
    Returns the frame as a base64 encoded JPEG.

    Security: Only admin users can access this endpoint.
    URL validation prevents command injection.
    """
    try:
        import cv2
    except ImportError:
        return jsonify({'error': 'OpenCV not installed. Run: pip install opencv-python'}), 500

    data = request.get_json()
    youtube_url = data.get('url')

    if not youtube_url:
        return jsonify({'error': 'YouTube URL is required'}), 400

    # SECURITY: Validate URL to prevent command injection
    if not validate_youtube_url(youtube_url):
        logger.warning(f"Invalid YouTube URL rejected: {youtube_url[:100]}")
        return jsonify({'error': 'Invalid YouTube URL. Only youtube.com and youtu.be URLs are allowed.'}), 400

    try:
        # Use yt-dlp Python API to get the direct video stream URL
        # SECURITY: No subprocess call - uses Python API directly
        stream_url = extract_video_url(youtube_url)

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

    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        return jsonify({'error': 'yt-dlp not installed. Run: pip install yt-dlp'}), 500
    except ValueError as e:
        logger.error(f"Video extraction error: {e}")
        return jsonify({'error': 'Failed to extract video URL. Check if the URL is valid.'}), 400
    except Exception as e:
        logger.error(f"Frame extraction error: {e}")
        # SECURITY: Don't leak internal error details to client
        return jsonify({'error': 'Frame extraction failed. Please try again.'}), 500


@admin_bp.route('/video-sources', methods=['POST'])
@admin_required
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
@admin_required
def get_video_sources():
    """Get all video sources."""
    sources = VideoSource.query.filter_by(is_active=True).all()
    return jsonify({
        'sources': [s.to_dict() for s in sources]
    })


@admin_bp.route('/video-sources/<int:source_id>', methods=['DELETE'])
@admin_required
def delete_video_source(source_id):
    """Delete a video source."""
    source = VideoSource.query.get_or_404(source_id)
    source.is_active = False
    db.session.commit()
    return jsonify({'message': 'Video source deleted'})


@admin_bp.route('/spaces-with-coordinates', methods=['GET'])
@admin_required
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
@admin_required
def create_bulk_spaces():
    """Create multiple parking spaces at once (from polygon drawing session)."""
    data = request.get_json()

    if not data or not data.get('spaces'):
        return jsonify({'error': 'Spaces array is required'}), 400

    location = data.get('location', 'Default Location')
    created_spaces = []

    skipped = []
    for idx, space_data in enumerate(data['spaces']):
        coordinates = space_data.get('coordinates', [])

        # Validate coordinates before creating space
        is_valid, error_msg = validate_coordinates(coordinates)
        if not is_valid:
            skipped.append({'index': idx, 'reason': error_msg})
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

    response = {
        'message': f'Created {len(created_spaces)} parking spaces',
        'spaces': [s.to_dict(include_coordinates=True) for s in created_spaces]
    }

    # Include skipped spaces info if any were invalid
    if skipped:
        response['skipped'] = skipped
        response['message'] += f', skipped {len(skipped)} invalid'

    return jsonify(response), 201


@admin_bp.route('/detection/config', methods=['GET'])
@admin_required
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
