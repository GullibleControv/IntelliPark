from flask import Blueprint, request, jsonify
import logging

from app.models import db, ParkingSpace, OccupancyLog
from app.utils.auth import token_required, optional_token

logger = logging.getLogger(__name__)

parking_bp = Blueprint('parking', __name__, url_prefix='/api/parking')


@parking_bp.route('/spaces', methods=['GET'])
def get_spaces():
    """Get all parking spaces with optional filters."""
    try:
        # Query parameters
        location = request.args.get('location')
        available_only = request.args.get('available', '').lower() == 'true'
        vehicle_type = request.args.get('vehicle_type')
        floor = request.args.get('floor')
        include_coords = request.args.get('include_coordinates', '').lower() == 'true'

        # Build query
        query = ParkingSpace.query.filter_by(is_active=True)

        if location:
            query = query.filter(ParkingSpace.location.ilike(f'%{location}%'))

        if available_only:
            query = query.filter_by(is_occupied=False)

        if vehicle_type:
            query = query.filter_by(vehicle_type=vehicle_type)

        if floor:
            query = query.filter_by(floor=floor)

        spaces = query.order_by(ParkingSpace.name).all()

        return jsonify({
            'spaces': [space.to_dict(include_coordinates=include_coords) for space in spaces],
            'total': len(spaces)
        })

    except Exception as e:
        logger.error(f"Get spaces error: {e}")
        return jsonify({'error': 'Failed to fetch parking spaces'}), 500


@parking_bp.route('/spaces/<int:space_id>', methods=['GET'])
def get_space(space_id):
    """Get a single parking space by ID."""
    try:
        space = ParkingSpace.query.get(space_id)

        if not space:
            return jsonify({'error': 'Parking space not found'}), 404

        return jsonify({'space': space.to_dict(include_coordinates=True)})

    except Exception as e:
        logger.error(f"Get space error: {e}")
        return jsonify({'error': 'Failed to fetch parking space'}), 500


@parking_bp.route('/spaces', methods=['POST'])
@token_required
def create_space():
    """Create a new parking space (admin only in production)."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Required fields
        name = data.get('name', '').strip()
        location = data.get('location', '').strip()

        if not name or not location:
            return jsonify({'error': 'Name and location are required'}), 400

        # Optional fields
        coordinates = data.get('coordinates')
        hourly_rate = data.get('hourly_rate', 50.0)
        vehicle_type = data.get('vehicle_type', 'car')
        floor = data.get('floor', 'G')

        # Validate coordinates if provided
        if coordinates:
            if not isinstance(coordinates, list) or len(coordinates) < 3:
                return jsonify({'error': 'Coordinates must be a list of at least 3 points'}), 400

        space = ParkingSpace(
            name=name,
            location=location,
            coordinates=coordinates,
            hourly_rate=float(hourly_rate),
            vehicle_type=vehicle_type,
            floor=floor
        )

        db.session.add(space)
        db.session.commit()

        logger.info(f"New parking space created: {space.name} at {space.location}")

        return jsonify({
            'message': 'Parking space created successfully',
            'space': space.to_dict(include_coordinates=True)
        }), 201

    except Exception as e:
        logger.error(f"Create space error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create parking space'}), 500


@parking_bp.route('/spaces/<int:space_id>', methods=['PUT'])
@token_required
def update_space(space_id):
    """Update a parking space."""
    try:
        space = ParkingSpace.query.get(space_id)

        if not space:
            return jsonify({'error': 'Parking space not found'}), 404

        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Update allowed fields
        if 'name' in data:
            space.name = data['name'].strip()

        if 'location' in data:
            space.location = data['location'].strip()

        if 'coordinates' in data:
            space.coordinates = data['coordinates']

        if 'hourly_rate' in data:
            space.hourly_rate = float(data['hourly_rate'])

        if 'vehicle_type' in data:
            space.vehicle_type = data['vehicle_type']

        if 'floor' in data:
            space.floor = data['floor']

        if 'is_active' in data:
            space.is_active = bool(data['is_active'])

        db.session.commit()

        return jsonify({
            'message': 'Parking space updated successfully',
            'space': space.to_dict(include_coordinates=True)
        })

    except Exception as e:
        logger.error(f"Update space error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update parking space'}), 500


@parking_bp.route('/spaces/<int:space_id>', methods=['DELETE'])
@token_required
def delete_space(space_id):
    """Delete (deactivate) a parking space."""
    try:
        space = ParkingSpace.query.get(space_id)

        if not space:
            return jsonify({'error': 'Parking space not found'}), 404

        # Soft delete - just mark as inactive
        space.is_active = False
        db.session.commit()

        logger.info(f"Parking space deactivated: {space.name}")

        return jsonify({'message': 'Parking space deleted successfully'})

    except Exception as e:
        logger.error(f"Delete space error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete parking space'}), 500


@parking_bp.route('/spaces/<int:space_id>/status', methods=['PUT'])
def update_space_status(space_id):
    """
    Update parking space occupancy status.
    This endpoint is called by the detection system.
    """
    try:
        space = ParkingSpace.query.get(space_id)

        if not space:
            return jsonify({'error': 'Parking space not found'}), 404

        data = request.get_json()

        if data is None or 'is_occupied' not in data:
            return jsonify({'error': 'is_occupied field is required'}), 400

        old_status = space.is_occupied
        new_status = bool(data['is_occupied'])

        # Only update and log if status changed
        if old_status != new_status:
            space.is_occupied = new_status

            # Log the change
            log_entry = OccupancyLog(
                space_id=space_id,
                is_occupied=new_status,
                confidence=data.get('confidence')
            )
            db.session.add(log_entry)
            db.session.commit()

            logger.debug(f"Space {space.name} status changed: {old_status} -> {new_status}")

        return jsonify({'success': True, 'is_occupied': space.is_occupied})

    except Exception as e:
        logger.error(f"Update status error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update status'}), 500


@parking_bp.route('/status', methods=['GET'])
def get_overall_status():
    """Get overall parking status summary."""
    try:
        location = request.args.get('location')

        query = ParkingSpace.query.filter_by(is_active=True)

        if location:
            query = query.filter(ParkingSpace.location.ilike(f'%{location}%'))

        spaces = query.all()

        total = len(spaces)
        occupied = sum(1 for s in spaces if s.is_occupied)
        available = total - occupied

        return jsonify({
            'total': total,
            'occupied': occupied,
            'available': available,
            'occupancy_rate': round((occupied / total * 100), 1) if total > 0 else 0,
            'spaces': [{'id': s.id, 'name': s.name, 'is_occupied': s.is_occupied} for s in spaces]
        })

    except Exception as e:
        logger.error(f"Get status error: {e}")
        return jsonify({'error': 'Failed to fetch status'}), 500


@parking_bp.route('/locations', methods=['GET'])
def get_locations():
    """Get list of unique parking locations."""
    try:
        locations = db.session.query(ParkingSpace.location).filter_by(
            is_active=True
        ).distinct().all()

        return jsonify({
            'locations': [loc[0] for loc in locations]
        })

    except Exception as e:
        logger.error(f"Get locations error: {e}")
        return jsonify({'error': 'Failed to fetch locations'}), 500
