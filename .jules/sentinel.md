## 2026-08-31 - Redacting Secrets in Dataclass Representations
**Vulnerability:** Python dataclasses generate a default `__repr__` that prints all field values in plaintext, exposing secret fields (e.g., `secret_token`) in log files, tracebacks, and debugging outputs.
**Learning:** Overriding `__repr__` on configuration or dataclass models that contain secret attributes allows safe logging of object instances without leaking sensitive credentials.
**Prevention:** Always define custom `__repr__` methods on dataclasses or configuration models containing secrets or tokens to redact them (e.g., `'***'`).
