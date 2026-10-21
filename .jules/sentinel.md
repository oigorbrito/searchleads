## 2026-08-31 - URL Scheme Validation in urllib.request Transport Boundaries
**Vulnerability:** External fetch adapters using `urllib.request.urlopen` accept any supported URL scheme by default (e.g., `file://`, `ftp://`), exposing the application to local file disclosure or protocol smuggling if untrusted or malformed URLs reach transport boundaries.
**Learning:** Checking `url.strip()` or status codes is insufficient; `urllib.parse.urlsplit` must explicitly enforce that `parsed.scheme.lower() in {'http', 'https'}` and `parsed.hostname` is present before making transport calls or constructing observation domain records.
**Prevention:** Validate URL schemes explicitly in data classes and transport functions across all network acquisition boundaries.
