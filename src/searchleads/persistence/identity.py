from __future__ import annotations

from .sqlite import PersistenceError
from .v3 import SQLiteRepository as _V3SQLiteRepository


class DomainRecordIdentityError(PersistenceError):
    """Raised when a decoded record ID disagrees with its persisted row key."""


class SQLiteRepository(_V3SQLiteRepository):
    """Public repository with physical-row/domain-record identity validation."""

    def load(self, record_type, record_id):
        record = super().load(record_type, record_id)
        if record is None:
            return None

        decoded_id = self._record_id(record)
        if decoded_id != record_id:
            raise DomainRecordIdentityError(
                f"{record_type.__name__} physical record id {record_id!r} "
                f"does not match decoded record id {decoded_id!r}"
            )
        return record
