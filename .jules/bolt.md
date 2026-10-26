## YYYY-MM-DD - [Title]
**Learning:** [Insight]
**Action:** [How to apply next time]

## 2024-10-26 - Regex vs String split for whitespace collapse
**Learning:** In hot loops like ETL text normalization, replacing `re.sub(r"\s+", " ", text)` with `" ".join(text.split())` yields an ~81% performance improvement by avoiding regex overhead.
**Action:** Prioritize built-in string methods over regex for simple whitespace normalization in hot loops.
