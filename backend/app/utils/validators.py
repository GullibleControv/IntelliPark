import re
from typing import Tuple


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password strength.
    Returns (is_valid, error_message)
    """
    if not password:
        return False, 'Password is required'

    if len(password) < 8:
        return False, 'Password must be at least 8 characters'

    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter'

    if not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter'

    if not re.search(r'[0-9]', password):
        return False, 'Password must contain at least one number'

    return True, ''


def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    if not phone:
        return True  # Phone is optional

    # Remove common separators
    cleaned = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    pattern = r'^\+?[0-9]{10,15}$'
    return bool(re.match(pattern, cleaned))


def validate_vehicle_number(vehicle_number: str) -> bool:
    """Validate vehicle registration number."""
    if not vehicle_number:
        return True  # Optional field

    # Basic validation - alphanumeric, 4-15 characters
    pattern = r'^[A-Z0-9\-\s]{4,15}$'
    return bool(re.match(pattern, vehicle_number.upper()))


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize a string input."""
    if not value:
        return ''
    # Strip whitespace and limit length
    return value.strip()[:max_length]
