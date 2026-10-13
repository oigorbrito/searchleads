## 2026-08-24 - Validate URLs at Transport Boundaries to Prevent Arbitrary Scheme Access
**Vulnerability:** HTTP fetch boundaries using `urllib.request.urlopen` directly without checking the URL scheme can be abused to fetch non-HTTP resources (e.g. `file://` local files) or leak credentials embedded in URLs.
**Learning:** Transport helpers must explicitly validate that incoming URLs use `http` or `https` schemes, contain a valid hostname, and carry no embedded user credentials prior to request instantiation.
**Prevention:** Always apply strict scheme and component checks via `urllib.parse.urlsplit` at all transport entrypoints.
