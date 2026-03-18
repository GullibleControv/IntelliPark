"""
Unit tests for auth utilities module.
Tests password hashing and JWT token functions.
"""
import pytest
import time
from datetime import datetime, timedelta

from app.utils.auth import (
    hash_password,
    verify_password,
    generate_token,
    decode_token
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    @pytest.mark.unit
    def test_hash_password_returns_string(self, app):
        """hash_password should return a string."""
        with app.app_context():
            result = hash_password('password123')
            assert isinstance(result, str)

    @pytest.mark.unit
    def test_hash_password_different_from_input(self, app):
        """Hashed password should differ from original."""
        with app.app_context():
            password = 'MySecurePassword123'
            hashed = hash_password(password)
            assert hashed != password

    @pytest.mark.unit
    def test_hash_password_unique_per_call(self, app):
        """Same password should produce different hashes (salt)."""
        with app.app_context():
            password = 'MySecurePassword123'
            hash1 = hash_password(password)
            hash2 = hash_password(password)
            assert hash1 != hash2

    @pytest.mark.unit
    def test_verify_password_correct(self, app):
        """verify_password should return True for correct password."""
        with app.app_context():
            password = 'MySecurePassword123'
            hashed = hash_password(password)
            assert verify_password(password, hashed) is True

    @pytest.mark.unit
    def test_verify_password_incorrect(self, app):
        """verify_password should return False for wrong password."""
        with app.app_context():
            hashed = hash_password('CorrectPassword123')
            assert verify_password('WrongPassword123', hashed) is False

    @pytest.mark.unit
    def test_verify_password_invalid_hash(self, app):
        """verify_password should return False for invalid hash."""
        with app.app_context():
            assert verify_password('password', 'invalid-hash') is False

    @pytest.mark.unit
    def test_verify_password_empty_password(self, app):
        """verify_password should handle empty password."""
        with app.app_context():
            hashed = hash_password('password')
            assert verify_password('', hashed) is False


class TestJWTTokens:
    """Tests for JWT token functions."""

    @pytest.mark.unit
    def test_generate_token_returns_string(self, app):
        """generate_token should return a string."""
        with app.app_context():
            token = generate_token(1)
            assert isinstance(token, str)
            assert len(token) > 0

    @pytest.mark.unit
    def test_generate_token_unique(self, app):
        """Different user IDs should produce different tokens."""
        with app.app_context():
            token1 = generate_token(1)
            token2 = generate_token(2)
            assert token1 != token2

    @pytest.mark.unit
    def test_decode_token_valid(self, app):
        """decode_token should decode a valid token."""
        with app.app_context():
            user_id = 42
            token = generate_token(user_id)
            payload = decode_token(token)

            assert payload is not None
            assert payload['user_id'] == user_id
            assert 'exp' in payload
            assert 'iat' in payload

    @pytest.mark.unit
    def test_decode_token_invalid(self, app):
        """decode_token should return None for invalid token."""
        with app.app_context():
            assert decode_token('invalid.token.here') is None
            assert decode_token('') is None
            assert decode_token('malformed') is None

    @pytest.mark.unit
    def test_decode_token_wrong_secret(self, app):
        """decode_token should fail with wrong secret."""
        import jwt
        with app.app_context():
            # Generate token with different secret
            payload = {
                'user_id': 1,
                'exp': datetime.utcnow() + timedelta(hours=1),
                'iat': datetime.utcnow()
            }
            token = jwt.encode(payload, 'wrong-secret', algorithm='HS256')
            assert decode_token(token) is None

    @pytest.mark.unit
    def test_token_contains_expiration(self, app):
        """Token payload should contain expiration time."""
        with app.app_context():
            token = generate_token(1)
            payload = decode_token(token)

            assert 'exp' in payload
            # Expiration should be in the future
            exp_time = datetime.utcfromtimestamp(payload['exp'])
            assert exp_time > datetime.utcnow()
