from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Protocol

from searchleads.domain import Evidence, Source, utc_now
from searchleads.sources.brasilapi import HTTPObservation


@dataclass(frozen=True, slots=True)
class AcquisitionRequest:
    request_id: str
    url: str
    source_id: str
    requested_at: datetime = field(default_factory=utc_now)
    purpose: str = "acquisition"

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be blank")
        if not self.url.strip():
            raise ValueError("url must not be blank")
        if not self.source_id.strip():
            raise ValueError("source_id must not be blank")
        if self.requested_at.tzinfo is None:
            raise ValueError("requested_at must be timezone-aware")
        if not self.purpose.strip():
            raise ValueError("purpose must not be blank")


@dataclass(frozen=True, slots=True)
class AcquisitionResponse:
    request_id: str
    url: str
    status_code: int
    raw_payload: str
    captured_at: datetime
    headers: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be blank")
        if not self.url.strip():
            raise ValueError("url must not be blank")
        if self.status_code < 100 or self.status_code > 599:
            raise ValueError("status_code must be a valid HTTP status")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")


class AcquisitionRuntimeAdapter(Protocol):
    def acquire(self, request: AcquisitionRequest) -> AcquisitionResponse: ...


Transport = Callable[[str], HTTPObservation]


@dataclass(frozen=True, slots=True)
class ReferenceAcquisitionRuntimeAdapter:
    """Thin runtime adapter around an explicit transport callable.

    The adapter is intentionally small: it turns a request into a transport
    call, preserves the transport response, and keeps evidence materialization
    separate from runtime selection.
    """

    source: Source
    transport: Transport

    def acquire(self, request: AcquisitionRequest) -> AcquisitionResponse:
        if request.source_id != self.source.source_id:
            raise ValueError("request source_id does not match the configured source")
        observation = self.transport(request.url)
        return AcquisitionResponse(
            request.request_id,
            observation.url,
            observation.status_code,
            observation.raw_payload,
            observation.captured_at,
            tuple(sorted((str(key), str(value)) for key, value in observation.headers.items())),
        )


def materialize_evidence(
    request: AcquisitionRequest,
    response: AcquisitionResponse,
) -> Evidence:
    if request.request_id != response.request_id:
        raise ValueError("request and response must share the same request_id")
    return Evidence(
        evidence_id=f"evidence:{request.request_id}",
        source_id=request.source_id,
        locator=response.url,
        captured_at=response.captured_at,
        raw_payload=response.raw_payload,
        metadata={
            "purpose": request.purpose,
            "request_id": request.request_id,
            "status_code": response.status_code,
            "headers": response.headers,
        },
    )


__all__ = [
    "AcquisitionRequest",
    "AcquisitionResponse",
    "AcquisitionRuntimeAdapter",
    "ReferenceAcquisitionRuntimeAdapter",
    "materialize_evidence",
]
