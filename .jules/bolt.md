## 2024-11-07 - [Unused Regex Optimization]
**Learning:** Found an unused regex `WHITESPACE_RE` in `src/bioetl/domain/mapping/organism_classification_constants.py` that was left over after an optimization in `organism_classification.py` replaced regex-based whitespace removal with `str.split()` and `" ".join()`.
**Action:** Remove the unused regex.
