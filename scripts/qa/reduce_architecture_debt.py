"""Legacy compatibility facade for architecture debt plan generation.

Prefer `python -m scripts.engineering.qa reduce-architecture-debt`.
"""

from __future__ import annotations

from scripts.engineering.qa.reduce_architecture_debt import main


if __name__ == "__main__":
    raise SystemExit(main())
