"""Legacy compatibility facade for architecture debt task generation.

Prefer `python -m scripts.engineering.qa generate-debt-tasks`.
"""

from __future__ import annotations

from scripts.engineering.qa.generate_architecture_debt_tasks import main


if __name__ == "__main__":
    raise SystemExit(main())
