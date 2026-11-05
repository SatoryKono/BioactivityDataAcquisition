## 2024-05-24 - Efficient Regex Sanitization
**Learning:** Multiple chained `.replace()` and `re.sub()` calls for text sanitization in hot paths (like telemetry tag normalization) incur significant execution overhead. A unified regex combining multiple patterns (e.g. `re.sub(r"[\W_]+", "_", text)` replacing non-word characters and underscores) is significantly faster.
**Action:** When sanitizing strings by collapsing unwanted characters into a single separator, use a single unified regex over multiple `.replace()` and `re.sub()` combinations to improve performance.
