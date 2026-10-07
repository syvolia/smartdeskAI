"""Password policy unit tests.

The policy is a security control, not a UI nicety. Each rule gets a
positive and negative test.
"""

import pytest

from app.core.exceptions import ValidationError
from app.core.password_policy import MIN_LENGTH, validate_password_strength


def test_rejects_short_password() -> None:
    with pytest.raises(ValidationError, match="at least"):
        validate_password_strength("Abc123!")


def test_rejects_common_password() -> None:
    # 12+ chars but in the blocklist.
    with pytest.raises(ValidationError, match="common"):
        validate_password_strength("password1234")


def test_rejects_password_without_digit() -> None:
    with pytest.raises(ValidationError, match="letters and digits"):
        validate_password_strength("Abcdefghijklm")


def test_rejects_password_without_letter() -> None:
    with pytest.raises(ValidationError, match="letters and digits"):
        validate_password_strength("123456789012")


def test_rejects_password_containing_email_local_part() -> None:
    with pytest.raises(ValidationError, match="email"):
        validate_password_strength(
            "george-secret-42", email="george@example.test"
        )


def test_accepts_strong_password() -> None:
    # Should not raise.
    validate_password_strength("Tr0ub4dor-and-3", email="someone@example.test")


def test_min_length_constant_is_at_least_twelve() -> None:
    # Guard against someone lowering the floor without a review.
    assert MIN_LENGTH >= 12