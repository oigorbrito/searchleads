# Bolt's Journal - SearchLeads Performance Learnings

## 2026-08-24 - Dataclass Field Reflection & StrEnum Subclass Checking in Domain Persistence
**Learning:** Calling `dataclasses.fields()` on every record serialization causes significant reflection overhead. Precomputing field names per record type yields a ~2.6x speedup. In Python 3.11+, `StrEnum` is a subclass of `str`. Using `type(value) in (str, int, float, bool)` fast-paths exact primitives (strings, ints, floats, bools, Nones) while allowing `StrEnum` instances (whose `type()` is the Enum class) to fall through to `isinstance(value, StrEnum)`, avoiding slow MRO checks for primitives (~1.4x speedup).
**Action:** When serializing fixed dataclass domain models, precompute field tuples and use exact type equality checks before MRO-based `isinstance()` inheritance checks for primitives.
