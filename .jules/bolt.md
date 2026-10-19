# Bolt's Journal - Critical Learnings

## 2026-10-19 - Fast-path field normalization & domain IP parsing
**Learning:** Instantiating wrapper dataclasses with strict `__post_init__` validation in entity resolution hot paths (`_wu4`) adds heavy object creation and validation overhead. Additionally, attempting `ipaddress.ip_address(host)` on standard domain names causes python exception unwinding on every domain comparison.
**Action:** Expose direct `normalize_field_value` helper function to avoid creating `CandidateFact` wrappers during ER comparison. Fast-path host IP parsing by checking for colons (IPv6) or pure digits/dots (IPv4) before calling `ipaddress.ip_address`.
