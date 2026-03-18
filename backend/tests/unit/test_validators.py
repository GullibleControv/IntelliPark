"""
Unit tests for validators module.
Tests validation functions in isolation.
"""
import pytest
from app.utils.validators import (
    validate_email,
    validate_password,
    validate_phone,
    validate_vehicle_number,
    sanitize_string
)


class TestValidateEmail:
    """Tests for email validation."""

    @pytest.mark.unit
    def test_valid_email(self):
        """Valid emails should return True."""
        valid_emails = [
            'user@example.com',
            'user.name@example.com',
            'user+tag@example.com',
            'user@subdomain.example.com',
            'USER@EXAMPLE.COM',
            '123@example.com',
        ]
        for email in valid_emails:
            assert validate_email(email) is True, f"Expected {email} to be valid"

    @pytest.mark.unit
    def test_invalid_email(self):
        """Invalid emails should return False."""
        invalid_emails = [
            '',
            'invalid',
            '@example.com',
            'user@',
            'user@.com',
            'user@example',
            'user space@example.com',
            None,
        ]
        for email in invalid_emails:
            assert validate_email(email) is False, f"Expected {email} to be invalid"


class TestValidatePassword:
    """Tests for password validation."""

    @pytest.mark.unit
    def test_valid_password(self):
        """Valid passwords should return (True, '')."""
        valid_passwords = [
            'Password1',
            'MyP@ssw0rd',
            'Abcdefgh1',
            'UPPER123lower',
        ]
        for password in valid_passwords:
            is_valid, error = validate_password(password)
            assert is_valid is True, f"Expected {password} to be valid, got error: {error}"
            assert error == ''

    @pytest.mark.unit
    def test_password_too_short(self):
        """Passwords under 8 characters should fail."""
        is_valid, error = validate_password('Pass1')
        assert is_valid is False
        assert 'at least 8 characters' in error

    @pytest.mark.unit
    def test_password_no_uppercase(self):
        """Passwords without uppercase should fail."""
        is_valid, error = validate_password('password123')
        assert is_valid is False
        assert 'uppercase' in error

    @pytest.mark.unit
    def test_password_no_lowercase(self):
        """Passwords without lowercase should fail."""
        is_valid, error = validate_password('PASSWORD123')
        assert is_valid is False
        assert 'lowercase' in error

    @pytest.mark.unit
    def test_password_no_number(self):
        """Passwords without numbers should fail."""
        is_valid, error = validate_password('PasswordABC')
        assert is_valid is False
        assert 'number' in error

    @pytest.mark.unit
    def test_empty_password(self):
        """Empty password should fail."""
        is_valid, error = validate_password('')
        assert is_valid is False
        assert 'required' in error


class TestValidatePhone:
    """Tests for phone number validation."""

    @pytest.mark.unit
    def test_valid_phone_numbers(self):
        """Valid phone numbers should return True."""
        valid_phones = [
            '+1234567890',
            '1234567890',
            '+12345678901234',
            '(123) 456-7890',
            '123-456-7890',
        ]
        for phone in valid_phones:
            assert validate_phone(phone) is True, f"Expected {phone} to be valid"

    @pytest.mark.unit
    def test_invalid_phone_numbers(self):
        """Invalid phone numbers should return False."""
        invalid_phones = [
            '123',  # Too short
            'abcdefghij',  # Letters
            '+1234567890123456',  # Too long
        ]
        for phone in invalid_phones:
            assert validate_phone(phone) is False, f"Expected {phone} to be invalid"

    @pytest.mark.unit
    def test_empty_phone_is_valid(self):
        """Empty phone should be valid (optional field)."""
        assert validate_phone('') is True
        assert validate_phone(None) is True


class TestValidateVehicleNumber:
    """Tests for vehicle number validation."""

    @pytest.mark.unit
    def test_valid_vehicle_numbers(self):
        """Valid vehicle numbers should return True."""
        valid_numbers = [
            'ABC-1234',
            'MH12AB1234',
            'KA 01 MN 1234',
            'DL1CAB1234',
        ]
        for number in valid_numbers:
            assert validate_vehicle_number(number) is True, f"Expected {number} to be valid"

    @pytest.mark.unit
    def test_invalid_vehicle_numbers(self):
        """Invalid vehicle numbers should return False."""
        invalid_numbers = [
            'AB',  # Too short
            'ABCDEFGHIJKLMNOPQRS',  # Too long
            'ABC@123',  # Special character
        ]
        for number in invalid_numbers:
            assert validate_vehicle_number(number) is False, f"Expected {number} to be invalid"

    @pytest.mark.unit
    def test_empty_vehicle_number_is_valid(self):
        """Empty vehicle number should be valid (optional field)."""
        assert validate_vehicle_number('') is True
        assert validate_vehicle_number(None) is True


class TestSanitizeString:
    """Tests for string sanitization."""

    @pytest.mark.unit
    def test_strips_whitespace(self):
        """Should strip leading and trailing whitespace."""
        assert sanitize_string('  hello  ') == 'hello'
        assert sanitize_string('\thello\n') == 'hello'

    @pytest.mark.unit
    def test_limits_length(self):
        """Should limit string to max_length."""
        long_string = 'a' * 300
        result = sanitize_string(long_string, max_length=100)
        assert len(result) == 100

    @pytest.mark.unit
    def test_default_max_length(self):
        """Default max_length should be 255."""
        long_string = 'a' * 300
        result = sanitize_string(long_string)
        assert len(result) == 255

    @pytest.mark.unit
    def test_empty_string(self):
        """Empty or None input should return empty string."""
        assert sanitize_string('') == ''
        assert sanitize_string(None) == ''

    @pytest.mark.unit
    def test_preserves_content(self):
        """Should preserve valid content."""
        assert sanitize_string('Hello World') == 'Hello World'
        assert sanitize_string('user@example.com') == 'user@example.com'
