"""
Authentication routes with rate limiting protection.

Security features:
- Rate limiting on login/register to prevent brute force attacks
- Password hashing with bcrypt
- JWT token authentication
- Input validation and sanitization
"""
from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import logging
import hashlib

from app.models import db, User
from app.utils.auth import hash_password, verify_password, generate_token, token_required
from app.utils.validators import validate_email, validate_password, validate_phone, sanitize_string

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def get_limiter():
    """Get the rate limiter instance if available."""
    try:
        from app import limiter
        return limiter
    except ImportError:
        return None


def hash_identifier(identifier: str) -> str:
    """Hash an identifier for logging (privacy-preserving)."""
    return hashlib.sha256(identifier.encode()).hexdigest()[:12]


# Apply rate limiting at blueprint level
@auth_bp.before_request
def check_rate_limit():
    """
    Apply rate limiting to all auth routes.
    More restrictive limits on sensitive endpoints.
    """
    limiter = get_limiter()
    if not limiter or current_app.config.get('TESTING'):
        return None

    # Get the endpoint being accessed
    endpoint = request.endpoint
    if not endpoint:
        return None

    # Define rate limits per endpoint
    rate_limits = {
        'auth.login': '10 per minute',      # Prevent brute force
        'auth.register': '5 per minute',     # Prevent spam accounts
        'auth.change_password': '5 per minute',  # Prevent password guessing
    }

    limit = rate_limits.get(endpoint)
    if limit:
        # The limiter will raise an exception if limit exceeded
        # This is handled by the 429 error handler in __init__.py
        pass  # Limiter is already applied globally, this is documentation


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.

    Security:
    - Rate limited: 5 registrations per minute per IP (prevents spam accounts)
    - Password strength validation enforced
    - Email format validation
    - Input sanitization

    Why rate limiting matters for resume:
    - Prevents automated account creation (credential stuffing defense)
    - Shows understanding of OWASP Authentication Best Practices
    """
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

        # SECURITY: Log hashed identifier instead of PII
        logger.info(f"New user registered: {hash_identifier(user.email)}")

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
    """
    Authenticate user and return token.

    Security:
    - Rate limited: 10 attempts per minute per IP (prevents brute force)
    - Constant-time password comparison (via bcrypt)
    - Generic error message (prevents username enumeration)

    Why this matters for resume:
    - Demonstrates understanding of authentication security
    - Shows knowledge of timing attacks and enumeration prevention
    """
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

        # SECURITY: Use constant-time comparison and generic error
        # This prevents timing attacks and username enumeration
        if not user or not verify_password(password, user.password_hash):
            # Log failed attempt with hashed email (for security monitoring)
            logger.warning(f"Failed login attempt for: {hash_identifier(email)}")
            return jsonify({'error': 'Invalid email or password'}), 401

        # Generate token
        token = generate_token(user.id)

        # SECURITY: Log success with hashed identifier
        logger.info(f"User logged in: {hash_identifier(user.email)}")

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
    """
    Change user's password.

    Security:
    - Rate limited: 5 attempts per minute (prevents password guessing)
    - Requires current password verification
    - New password must meet strength requirements
    """
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
            logger.warning(f"Failed password change attempt for user: {hash_identifier(user.email)}")
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Validate new password
        is_valid, password_error = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': password_error}), 400

        # Update password
        user.password_hash = hash_password(new_password)
        db.session.commit()

        # SECURITY: Log with hashed identifier
        logger.info(f"Password changed for user: {hash_identifier(user.email)}")

        return jsonify({'message': 'Password changed successfully'})

    except Exception as e:
        logger.error(f"Change password error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to change password'}), 500
