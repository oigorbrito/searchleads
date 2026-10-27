# Sentinel Security Learnings

## 2026-08-24 - Validate PRAGMA inputs in SQLite Repository
**Vulnerability:** Dynamic string formatting in SQLite PRAGMA statements (`PRAGMA user_version = {version}`) without strict type checking allowed possible SQL injection if non-integer arguments were passed.
**Learning:** Parameter binding `?` is not supported in SQLite `PRAGMA` statements. String interpolation is necessary for setting PRAGMA pragmas dynamically.
**Prevention:** Always perform strict type checking (`type(version) is int`) and range checks before interpolating variables into SQLite PRAGMA execution queries.
