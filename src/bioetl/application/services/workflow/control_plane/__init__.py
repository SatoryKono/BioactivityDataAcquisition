"""Workflow-owned state-transition orchestration.

Immutable manifest, append-only ledger, and inspection services remain under
``application.services.control_plane.workflow``. This package owns execution,
resume, and state-transition coordination around those control-plane services.
"""

from __future__ import annotations
