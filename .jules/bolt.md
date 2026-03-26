## 2026-03-26 - [Optimize PyArrow .as_py() conversion in comprehensions]
**Learning:** PyArrow's `v.as_py()` method is expensive when converting scalars to Python objects. When iterating over PyArrow arrays/columns in a list comprehension, evaluating it multiple times per element (e.g. for condition and value assignment) causes significant performance overhead.
**Action:** Always avoid calling `.as_py()` multiple times per element. Use the walrus operator (`val := v.as_py()`) to evaluate and cache it once for both the condition and the value.
