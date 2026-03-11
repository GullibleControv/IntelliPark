from flask import Blueprint, request, jsonify
import logging

from app.models import db, User
from app.utils.auth import hash_password, verify_password, generate_token, token_required
from app.utils.validators import validate_email, validate_password, validate_phone, sanitize_string

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Extract and sanitize fields
        email = sanitize_string(data.get('email', ''))
        password = data.get('password', '')
        name = sanitize_string(data.get('name', ''))
        phone = sanitize_string(data.get('phone', ''))

        # Validation
        if not email or not password or not name:
            return jsonify({'error': 'Email, password, and name are required'}), 400

        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400

        is_valid_password, password_error = validate_password(password)
        if not is_valid_password:
            return jsonify({'error': password_error}), 400

        if phone and not validate_phone(phone):
            return jsonify({'error': 'Invalid phone number format'}), 400

        # Check if user already exists
        existing_user = User.query.filter_by(email=email.lower()).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 409

        # Create new user
        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            name=name,
            phone=phone if phone else None
        )

        db.session.add(user)
        db.session.commit()

        # Generate token
        token = generate_token(user.id)

        logger.info(f"New user registered: {user.email}")

        return jsonify({
            'message': 'Registration successful',
            'token': token,
            'user': user.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Registration error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Registration failed. Please try again.'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return token."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        email = sanitize_string(data.get('email', ''))
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Find user
        user = User.query.filter_by(email=email.lower()).first()

        if not user or not verify_password(password, user.password_hash):
            return jsonify({'error': 'Invalid email or password'}), 401

        # Generate token
        token = generate_token(user.id)

        logger.info(f"User logged in: {user.email}")

        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': user.to_dict()
        })

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed. Please try again.'}), 500


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    """Get current authenticated user's profile."""
    try:
        user = User.query.get(request.user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'user': user.to_dict()})

    except Exception as e:
        logger.error(f"Get profile error: {e}")
        return jsonify({'error': 'Failed to fetch profile'}), 500


@auth_bp.route('/me', methods=['PUT'])
@token_required
def update_current_user():
    """Update current user's profile."""
    try:
        user = User.query.get(request.user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Update allowed fields
        if 'name' in data:
            name = sanitize_string(data['name'])
            if name:
                user.name = name

        if 'phone' in data:
            phone = sanitize_string(data['phone'])
            if phone and not validate_phone(phone):
                return jsonify({'error': 'Invalid phone number format'}), 400
            user.phone = phone if phone else None

        db.session.commit()

        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        })

    except Exception as e:
        logger.error(f"Update profile error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile'}), 500


@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password():
    """Change user's password."""
    try:
        user = User.query.get(request.user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')

        if not current_password or not new_password:
            return jsonify({'error': 'Current and new password are required'}), 400

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Validate new password
        is_valid, password_error = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': password_error}), 400

        # Update password
        user.password_hash = hash_password(new_password)
        db.session.commit()

        logger.info(f"Password changed for user: {user.email}")

        return jsonify({'message': 'Password changed successfully'})

    except Exception as e:
        logger.error(f"Change password error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to change password'}), 500
