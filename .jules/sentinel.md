## 2026-08-26 - Network Transport URL Scheme Validation
**Vulnerability:** HTTP client handlers using `urllib.request.urlopen` in `brasilapi.py` and `apify.py` lacked scheme and hostname validation before invoking network calls.
**Learning:** Python's `urllib.request.urlopen` natively supports arbitrary schemes like `file://` or `ftp://`. Unless scheme and hostname presence are validated using `urllib.parse.urlsplit` before calling `urlopen`, passing arbitrary URLs can lead to SSRF or local file exposure.
**Prevention:** Always validate that incoming URLs use `http` or `https` schemes with a non-empty `hostname` prior to passing them to `urlopen`.
