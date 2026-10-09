"""Project-wide email type.

Uses `email-validator` under the hood but allows reserved-domain
addresses (`@example.test`, `@invalid`, etc.). The reserved-domain block
in email-validator is meant for outbound-deliverable addresses. Support
ticket systems store arbitrary addresses that are never actually emailed
— test fixtures, demo data, internal notes — so the strict check causes
more harm than good here.

If you specifically need the strict behaviour, import `EmailStr` from
`pydantic` in that module instead of this one.
"""

from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator


def _validate_email(value: str) -> str:
    try:
        result = validate_email(
            value,
            check_deliverability=False,
            # `test_environment=True` lifts the block on reserved TLDs
            # such as `.test`, `.example`, `.invalid`, and `.localhost`.
            test_environment=True,
        )
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc
    return result.normalized


EmailStr = Annotated[str, AfterValidator(_validate_email)]