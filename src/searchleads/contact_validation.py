from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit

from .domain import ContactPoint, ContactValidation, ContactValidationStatus

BASIC_SYNTAX_ONLY_V1 = "BASIC_SYNTAX_ONLY_V1"
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_contact_syntax(contact: ContactPoint) -> ContactValidation:
    """Validate only obvious syntax; plausible contact points remain UNKNOWN."""

    status = _syntax_status(contact)
    digest = hashlib.sha256(
        f"{contact.id}\0{BASIC_SYNTAX_ONLY_V1}\0{status.value}".encode("utf-8")
    ).hexdigest()
    return ContactValidation(
        id=f"contact-validation:sha256:{digest}",
        contact_point_id=contact.id,
        status=status,
        rule=BASIC_SYNTAX_ONLY_V1,
    )


def validate_contacts_syntax(
    contacts: tuple[ContactPoint, ...],
) -> tuple[ContactValidation, ...]:
    return tuple(validate_contact_syntax(contact) for contact in contacts)


def _syntax_status(contact: ContactPoint) -> ContactValidationStatus:
    kind = contact.kind.upper()
    if kind == "EMAIL":
        return (
            ContactValidationStatus.UNKNOWN
            if _EMAIL.fullmatch(contact.value) is not None
            else ContactValidationStatus.INVALID
        )
    if kind == "PHONE":
        digits = "".join(character for character in contact.value if character.isdigit())
        allowed = all(
            character.isdigit() or character in "+-(). " for character in contact.value
        )
        return (
            ContactValidationStatus.UNKNOWN
            if allowed and 7 <= len(digits) <= 15
            else ContactValidationStatus.INVALID
        )
    if kind == "URL":
        try:
            parsed = urlsplit(contact.value)
        except ValueError:
            return ContactValidationStatus.INVALID
        return (
            ContactValidationStatus.UNKNOWN
            if parsed.scheme in {"http", "https"} and bool(parsed.hostname)
            else ContactValidationStatus.INVALID
        )
    return ContactValidationStatus.INVALID
