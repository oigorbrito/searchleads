## 2026-03-30 - [Fast-path `@` check before `_EMAIL_RE.finditer()` regex]
**Learning:** Running complex case-insensitive email regex search (`_EMAIL_RE.finditer`) on large scraped web text or HTML blocks is expensive when no emails are present. Substring check (`'@' in text`) is C-accelerated in Python and operates in O(N) time with minimal constant factors, avoiding regex evaluation overhead when no email exists.
**Action:** Always place a fast character check (e.g. `'@' in text`) before running email regex patterns on arbitrary text/HTML blocks.
