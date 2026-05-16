"""Repository-local Python startup hooks.

Keep memory tooling from emitting bytecode caches under ``src/memory`` during
routine ``python -m memory...`` commands. The memory validator intentionally
fails closed on working-tree caches in that subtree.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True
