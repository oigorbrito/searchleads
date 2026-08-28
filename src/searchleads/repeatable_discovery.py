from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class ReplayIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class KnownSourcePlan:
    id: str
    url: str
    parser_id: str
    expected_schema_fingerprint: str

    @property
    def fingerprint(self) -> str:
        payload = {
            "id": self.id,
            "url": self.url,
            "parser_id": self.parser_id,
            "expected_schema_fingerprint": self.expected_schema_fingerprint,
        }
        return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AcquisitionRecord:
    evidence_sha256: str
    plan_fingerprint: str
    schema_fingerprint: str


class EvidenceCache:
    """Immutable content-addressed cache keyed by SHA-256."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, raw_content: bytes) -> str:
        if not isinstance(raw_content, bytes):
            raise TypeError("raw_content must be bytes")
        digest = hashlib.sha256(raw_content).hexdigest()
        target = self.root / digest
        try:
            with target.open("xb") as stream:
                stream.write(raw_content)
        except FileExistsError:
            if target.read_bytes() != raw_content:
                raise ReplayIntegrityError("content-addressed cache collision or mutation detected")
        return digest

    def get(self, digest: str) -> bytes:
        if not _is_sha256(digest):
            raise ValueError("digest must be a lowercase SHA-256 hex string")
        target = self.root / digest
        if not target.exists():
            raise KeyError(digest)
        raw = target.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ReplayIntegrityError("cached Evidence no longer matches its content address")
        return raw


def record_acquisition(
    plan: KnownSourcePlan,
    raw_content: bytes,
    *,
    cache: EvidenceCache,
    schema_fingerprint: Callable[[bytes], str],
) -> AcquisitionRecord:
    observed_schema = schema_fingerprint(raw_content)
    if observed_schema != plan.expected_schema_fingerprint:
        raise ReplayIntegrityError("source schema drifted from KnownSourcePlan")
    digest = cache.put(raw_content)
    return AcquisitionRecord(
        evidence_sha256=digest,
        plan_fingerprint=plan.fingerprint,
        schema_fingerprint=observed_schema,
    )


def replay_acquisition(
    plan: KnownSourcePlan,
    record: AcquisitionRecord,
    *,
    cache: EvidenceCache,
    schema_fingerprint: Callable[[bytes], str],
) -> bytes:
    if record.plan_fingerprint != plan.fingerprint:
        raise ReplayIntegrityError("KnownSourcePlan fingerprint changed since acquisition")
    if record.schema_fingerprint != plan.expected_schema_fingerprint:
        raise ReplayIntegrityError("recorded schema no longer matches KnownSourcePlan")

    raw = cache.get(record.evidence_sha256)
    observed_schema = schema_fingerprint(raw)
    if observed_schema != record.schema_fingerprint:
        raise ReplayIntegrityError("cached Evidence schema differs from recorded acquisition")
    return raw


def sec_company_tickers_schema_fingerprint(raw_content: bytes) -> str:
    try:
        payload = json.loads(raw_content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReplayIntegrityError("cannot fingerprint invalid JSON schema") from exc
    if not isinstance(payload, dict):
        raise ReplayIntegrityError("SEC schema root must be an object")
    fields = payload.get("fields")
    if not isinstance(fields, list) or not all(isinstance(item, str) for item in fields):
        raise ReplayIntegrityError("SEC schema fields must be a string array")
    return hashlib.sha256(_stable_json(fields).encode("utf-8")).hexdigest()


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)
