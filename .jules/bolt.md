
## 2025-02-17 - [Avoid Regex for Simple Character Replacements and String Operations]
**Learning:** In ETL hot-loops (`bioetl.domain.mapping`), `re.sub` for whitespace collapsing and simple substring replacements creates significant overhead. In the case of organism name normalization, combining conditionally checking for parenthesis `if "(" in text:` with python's built in `" ".join(text.split())` instead of regex `\s+` substitutions yields a ~2.3x performance boost.
**Action:** When working on text normalization loops, prefer simple conditional checks and string methods (like `split()`, `join()`, `strip()`, `find()`) over regex when possible, and only invoke regex transformations conditionally.
