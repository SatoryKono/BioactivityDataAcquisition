#!/usr/bin/env python3
"""
salt_rotate.py - Rotate PII hashing salt for security compliance.

Manages the rotation of salts used for PII hashing in the Silver layer.
Supports dual-salt rotation for graceful transitions and emergency
rotation for security incidents.

The rotation process:
1. Generate new salt and set as BIOETL_PII_SALT_NEXT
2. Enable transition period (BIOETL_SALT_ROTATION_ACTIVE=true)
3. During transition, both salts are valid for lookups
4. After transition, promote NEXT to CURRENT
5. Remove old salt

Usage:
    # Standard rotation (initiates transition period)
    python src/tools/salt_rotate.py

    # Emergency rotation (immediate, no transition)
    python src/tools/salt_rotate.py --emergency

    # Verify current salt configuration
    python src/tools/salt_rotate.py --verify

    # Complete transition (promote NEXT to CURRENT)
    python src/tools/salt_rotate.py --complete

References:
    - RULES.md §5.4.1: Dual-Salt Rotation
    - SaltManager in src/bioetl/infrastructure/security/

Aligned with RULES.md v5.24 (2026-01-06)
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import secrets
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# Configure logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Environment variable names
ENV_SALT_CURRENT = "BIOETL_PII_SALT_CURRENT"
ENV_SALT_NEXT = "BIOETL_PII_SALT_NEXT"
ENV_ROTATION_ACTIVE = "BIOETL_SALT_ROTATION_ACTIVE"

# Salt requirements
MIN_SALT_LENGTH = 32
RECOMMENDED_SALT_LENGTH = 64


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class SaltStatus:
    """Current salt configuration status."""

    current_salt_set: bool
    current_salt_id: str | None
    current_salt_length: int | None
    next_salt_set: bool
    next_salt_id: str | None
    next_salt_length: int | None
    rotation_active: bool
    valid: bool
    issues: list[str]


@dataclass
class RotationResult:
    """Result of salt rotation operation."""

    success: bool
    action: str
    new_salt_id: str | None = None
    env_updates: dict[str, str | None] | None = None
    message: str = ""
    error: str | None = None


# =============================================================================
# Salt Functions
# =============================================================================


def generate_salt(length: int = RECOMMENDED_SALT_LENGTH) -> str:
    """Generate a cryptographically secure salt.

    Args:
        length: Desired length in characters (hex encoded).

    Returns:
        Hex-encoded random salt string.
    """
    # Generate length/2 bytes (since hex encoding doubles length)
    salt_bytes = secrets.token_bytes(length // 2)
    return salt_bytes.hex()


def get_salt_id(salt: str) -> str:
    """Get short identifier for a salt (first 8 chars of SHA256).

    Args:
        salt: The salt value.

    Returns:
        8-character identifier.
    """
    return hashlib.sha256(salt.encode("utf-8")).hexdigest()[:8]


def get_current_status() -> SaltStatus:
    """Get current salt configuration status.

    Returns:
        SaltStatus with current configuration details.
    """
    current_salt = os.environ.get(ENV_SALT_CURRENT, "")
    next_salt = os.environ.get(ENV_SALT_NEXT, "")
    rotation_active = os.environ.get(ENV_ROTATION_ACTIVE, "").lower() in (
        "true",
        "1",
        "yes",
    )

    issues = []

    # Check current salt
    current_set = bool(current_salt)
    current_id = get_salt_id(current_salt) if current_salt else None
    current_len = len(current_salt) if current_salt else None

    if not current_set:
        issues.append(f"{ENV_SALT_CURRENT} is not set")
    elif current_len and current_len < MIN_SALT_LENGTH:
        issues.append(
            f"{ENV_SALT_CURRENT} is too short ({current_len} < {MIN_SALT_LENGTH})"
        )

    # Check next salt
    next_set = bool(next_salt)
    next_id = get_salt_id(next_salt) if next_salt else None
    next_len = len(next_salt) if next_salt else None

    if rotation_active and not next_set:
        issues.append(f"Rotation active but {ENV_SALT_NEXT} is not set")

    if next_set and next_len and next_len < MIN_SALT_LENGTH:
        issues.append(f"{ENV_SALT_NEXT} is too short ({next_len} < {MIN_SALT_LENGTH})")

    return SaltStatus(
        current_salt_set=current_set,
        current_salt_id=current_id,
        current_salt_length=current_len,
        next_salt_set=next_set,
        next_salt_id=next_id,
        next_salt_length=next_len,
        rotation_active=rotation_active,
        valid=len(issues) == 0,
        issues=issues,
    )


def initiate_rotation() -> RotationResult:
    """Initiate a new salt rotation with transition period.

    Generates a new salt and sets it as NEXT salt.
    Enables rotation mode for dual-salt validation.

    Returns:
        RotationResult with operation details.
    """
    status = get_current_status()

    if not status.current_salt_set:
        return RotationResult(
            success=False,
            action="initiate",
            error=f"{ENV_SALT_CURRENT} must be set before rotation can be initiated",
        )

    if status.rotation_active:
        return RotationResult(
            success=False,
            action="initiate",
            error="Rotation already in progress. Complete or cancel first.",
        )

    # Generate new salt
    new_salt = generate_salt()
    new_salt_id = get_salt_id(new_salt)

    return RotationResult(
        success=True,
        action="initiate",
        new_salt_id=new_salt_id,
        env_updates={
            ENV_SALT_NEXT: new_salt,
            ENV_ROTATION_ACTIVE: "true",
        },
        message=f"New salt generated (ID: {new_salt_id}). Transition period initiated.",
    )


def complete_rotation() -> RotationResult:
    """Complete salt rotation by promoting NEXT to CURRENT.

    Returns:
        RotationResult with operation details.
    """
    status = get_current_status()

    if not status.rotation_active:
        return RotationResult(
            success=False,
            action="complete",
            error="No rotation in progress. Nothing to complete.",
        )

    if not status.next_salt_set:
        return RotationResult(
            success=False,
            action="complete",
            error=f"{ENV_SALT_NEXT} is not set. Cannot complete rotation.",
        )

    next_salt = os.environ.get(ENV_SALT_NEXT, "")
    if len(next_salt) < MIN_SALT_LENGTH:
        return RotationResult(
            success=False,
            action="complete",
            error=(
                f"{ENV_SALT_NEXT} is too short "
                f"({len(next_salt)} < {MIN_SALT_LENGTH})"
            ),
        )

    return RotationResult(
        success=True,
        action="complete",
        new_salt_id=status.next_salt_id,
        env_updates={
            ENV_SALT_CURRENT: next_salt,
            ENV_SALT_NEXT: None,  # Clear
            ENV_ROTATION_ACTIVE: "false",
        },
        message=f"Rotation completed. NEXT salt (ID: {status.next_salt_id}) promoted to CURRENT.",
    )


def emergency_rotation() -> RotationResult:
    """Perform emergency salt rotation without transition period.

    Immediately replaces current salt with a new one.
    USE WITH CAUTION: Existing hashes will become invalid.

    Returns:
        RotationResult with operation details.
    """
    # Generate new salt
    new_salt = generate_salt()
    new_salt_id = get_salt_id(new_salt)

    return RotationResult(
        success=True,
        action="emergency",
        new_salt_id=new_salt_id,
        env_updates={
            ENV_SALT_CURRENT: new_salt,
            ENV_SALT_NEXT: None,  # Clear any pending rotation
            ENV_ROTATION_ACTIVE: "false",
        },
        message=f"EMERGENCY: Salt immediately rotated (ID: {new_salt_id}). Previous hashes INVALIDATED.",
    )


def cancel_rotation() -> RotationResult:
    """Cancel ongoing rotation.

    Returns:
        RotationResult with operation details.
    """
    status = get_current_status()

    if not status.rotation_active:
        return RotationResult(
            success=False,
            action="cancel",
            error="No rotation in progress. Nothing to cancel.",
        )

    return RotationResult(
        success=True,
        action="cancel",
        env_updates={
            ENV_SALT_NEXT: None,
            ENV_ROTATION_ACTIVE: "false",
        },
        message="Rotation cancelled. NEXT salt cleared.",
    )


# =============================================================================
# CLI Interface
# =============================================================================


def log_status(status: SaltStatus) -> None:
    """Log current salt status."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("BioETL PII Salt Status")
    logger.info("=" * 70)
    logger.info("")

    # Current salt
    logger.info("## Current Salt")
    if status.current_salt_set:
        logger.info("  Status:   SET")
        logger.info("  ID:       %s", status.current_salt_id)
        logger.info("  Length:   %d characters", status.current_salt_length)
    else:
        logger.info("  Status:   NOT SET")
    logger.info("")

    # Next salt
    logger.info("## Next Salt (Rotation)")
    if status.next_salt_set:
        logger.info("  Status:   SET")
        logger.info("  ID:       %s", status.next_salt_id)
        logger.info("  Length:   %d characters", status.next_salt_length)
    else:
        logger.info("  Status:   NOT SET")
    logger.info("")

    # Rotation status
    logger.info("## Rotation Status")
    if status.rotation_active:
        logger.info("  Active:   YES (transition period)")
    else:
        logger.info("  Active:   NO")
    logger.info("")

    # Issues
    if status.issues:
        logger.info("## Issues")
        for issue in status.issues:
            logger.info("  - %s", issue)
        logger.info("")

    # Overall status
    logger.info("=" * 70)
    if status.valid:
        logger.info("Configuration: VALID")
    else:
        logger.info("Configuration: INVALID - see issues above")
    logger.info("=" * 70)


def log_result(result: RotationResult) -> None:
    """Log rotation result."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Salt Rotation Result")
    logger.info("=" * 70)
    logger.info("")

    logger.info("Action:  %s", result.action.upper())
    logger.info("Success: %s", "YES" if result.success else "NO")
    logger.info("")

    if result.success:
        _log_success_result(result)
    else:
        logger.info("Error: %s", result.error)

    logger.info("")
    logger.info("=" * 70)


def _log_success_result(result: RotationResult) -> None:
    logger.info("Message: %s", result.message)
    logger.info("")

    if result.new_salt_id:
        logger.info("New Salt ID: %s", result.new_salt_id)
    logger.info("")

    if not result.env_updates:
        return

    logger.info("## Required Environment Updates")
    logger.info("")
    logger.info("Add/update these in your environment or .env file:")
    logger.info("")
    for key, value in result.env_updates.items():
        logger.info("  %s", _format_env_update(key, value))
    logger.info("")
    logger.info("NOTE: This tool does NOT modify your environment.")
    logger.info("      You must update these values manually.")


def _format_env_update(key: str, value: str | None) -> str:
    if value is None:
        return f"unset {key}"
    display_value = value[:16] + "..." if len(value) > 20 else value
    return f"{key}={display_value}"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="BioETL PII Salt Rotation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--verify",
        action="store_true",
        help="Verify current salt configuration (default)",
    )
    group.add_argument(
        "--initiate",
        action="store_true",
        help="Initiate new salt rotation (transition period)",
    )
    group.add_argument(
        "--complete",
        action="store_true",
        help="Complete ongoing rotation (promote NEXT to CURRENT)",
    )
    group.add_argument(
        "--cancel",
        action="store_true",
        help="Cancel ongoing rotation",
    )
    group.add_argument(
        "--emergency",
        action="store_true",
        help="Emergency rotation (immediate, invalidates existing hashes)",
    )

    return parser.parse_args()


def _exit_code(result: RotationResult) -> int:
    log_result(result)
    return 0 if result.success else 1


def _log_emergency_warning() -> None:
    logger.warning("")
    logger.warning("!" * 70)
    logger.warning("! EMERGENCY SALT ROTATION")
    logger.warning("!" * 70)
    logger.warning("!")
    logger.warning("! This will IMMEDIATELY invalidate ALL existing PII hashes!")
    logger.warning("! Records hashed with the old salt CANNOT be matched.")
    logger.warning("!")
    logger.warning("! Use only in case of:")
    logger.warning("!   - Security incident (salt compromised)")
    logger.warning("!   - Regulatory requirement")
    logger.warning("!")
    logger.warning("!" * 70)
    logger.warning("")


def _run_requested_action(args: argparse.Namespace) -> RotationResult | None:
    actions: list[tuple[str, Callable[[], RotationResult]]] = [
        ("initiate", initiate_rotation),
        ("complete", complete_rotation),
        ("cancel", cancel_rotation),
    ]
    for attr, action in actions:
        if getattr(args, attr):
            return action()
    if args.emergency:
        _log_emergency_warning()
        return emergency_rotation()
    return None


def main() -> int:
    """Entry point."""
    args = parse_args()

    # Get current status first
    status = get_current_status()
    result = _run_requested_action(args)
    if result is not None:
        return _exit_code(result)

    # Default: verify status
    log_status(status)
    return 0 if status.valid else 1


if __name__ == "__main__":
    sys.exit(main())
