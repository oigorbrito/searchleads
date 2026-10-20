## 2026-08-25 - URL Scheme and Host Validation for urllib Transports
**Vulnerability:** `urllib.request.urlopen` default handlers accept schemes like `file://` or `ftp://` and execute file read/network operations, exposing potential Local File Inclusion (LFI) or unexpected protocol handlers when processing unvalidated URL inputs in transport functions like `http_get`.
**Learning:** Standard HTTP transport implementations using `urllib` must explicitly validate that the URL scheme is `http` or `https` and includes a non-empty hostname before invoking `urlopen`.
**Prevention:** Validate URL scheme and hostname using `urlsplit(url)` prior to calling `urllib.request.urlopen` in all transport adapters.
