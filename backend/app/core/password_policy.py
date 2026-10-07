"""Password strength validation.

Enforced on registration and admin-created users. Not enforced on
existing sessions — a validator that fails on login would break users
whose password predates the policy.
"""

from app.core.exceptions import ValidationError

MIN_LENGTH = 12

# Small embedded list — replace with a bloom filter over a large
# dictionary for production scale.
_COMMON = {
    "password", "passw0rd", "123456789012", "qwertyuiop12",
    "letmein12345", "welcome12345", "admin1234567", "changeme1234",
    "smartdesk123", "smartdesk!23",
}


def validate_password_strength(password: str, *, email: str | None = None) -> None:
    if len(password) < MIN_LENGTH:
        raise ValidationError(f"Password must be at least {MIN_LENGTH} characters.")

    if password.lower() in _COMMON:
        raise ValidationError("Password is too common.")

    if email:
        local = email.split("@", 1)[0].lower()
        if len(local) >= 4 and local in password.lower():
            raise ValidationError("Password must not contain your email name.")

    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_letter and has_digit):
        raise ValidationError("Password must contain letters and digits.")