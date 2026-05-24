"""Tests for password hashing and JWT utilities."""

import pytest
from jose import JWTError

from idp_app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_password_returns_string(self) -> None:
        hashed = hash_password("mysecret")
        assert isinstance(hashed, str)
        assert hashed != "mysecret"

    def test_verify_password_correct(self) -> None:
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", hashed) is True

    def test_verify_password_wrong(self) -> None:
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("wrong-password", hashed) is False

    def test_different_hashes_for_same_password(self) -> None:
        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        # bcrypt generates a unique salt each time
        assert h1 != h2


class TestJWT:
    def test_create_and_decode_token(self) -> None:
        token = create_access_token({"sub": "alice"})
        payload = decode_access_token(token)
        assert payload["sub"] == "alice"

    def test_token_contains_expiry(self) -> None:
        token = create_access_token({"sub": "bob"})
        payload = decode_access_token(token)
        assert "exp" in payload

    def test_invalid_token_raises(self) -> None:
        with pytest.raises(JWTError):
            decode_access_token("not.a.valid.token")
