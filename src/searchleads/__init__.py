"""SearchLeads scientific domain foundation."""

from .domain import (
    CandidateFact,
    CanonicalFact,
    Company,
    ContactPoint,
    ContactValidation,
    ContactValidationStatus,
    DomainInvariantError,
    Evidence,
    Lead,
    Person,
    ProfessionalRole,
    ReviewCase,
    ReviewReason,
    Source,
)
from .persistence import CURRENT_SCHEMA_VERSION, SQLiteStore, UnsupportedSchemaVersion

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "CandidateFact",
    "CanonicalFact",
    "Company",
    "ContactPoint",
    "ContactValidation",
    "ContactValidationStatus",
    "DomainInvariantError",
    "Evidence",
    "Lead",
    "Person",
    "ProfessionalRole",
    "ReviewCase",
    "ReviewReason",
    "SQLiteStore",
    "Source",
    "UnsupportedSchemaVersion",
]
