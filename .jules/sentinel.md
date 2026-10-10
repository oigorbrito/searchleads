## 2026-08-24 - SQLite PRAGMA Statement Parameterization Pattern
**Vulnerability:** Python `sqlite3` driver does not allow parameter substitution (`?`) in `PRAGMA` statements like `PRAGMA user_version = ?`. Using f-strings naively without strict type checking opens potential SQL injection risks if non-integer inputs reach persistence internals.
**Learning:** SQLite PRAGMA statements require static literals or strictly validated string formatting.
**Prevention:** Strictly validate `isinstance(version, int) and not isinstance(version, bool)` and explicitly cast to `int(version)` prior to formatting `PRAGMA user_version = {int(version)}`.
