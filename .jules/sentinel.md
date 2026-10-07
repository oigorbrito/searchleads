# Sentinel Security Journal

## 2026-10-07 - Redact Secret Token Fields in Dataclass Representations
**Vulnerability:** Dataclasses holding operational or runtime secrets (e.g. `OperationalConfiguration.secret_token`) expose secret values in plaintext when converted to string or printed in logs/error traces via auto-generated `__repr__`.
**Learning:** Python dataclasses generate `__repr__` for all defined fields by default unless explicitly configured otherwise.
**Prevention:** Always set `repr=False` on dataclass fields holding tokens, API keys, passwords, or secrets (e.g., `secret_token: str | None = field(default=None, repr=False)`).
