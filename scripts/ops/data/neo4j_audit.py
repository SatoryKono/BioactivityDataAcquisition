"""
Neo4j connection helper for audit workload.

Usage:
    from src.tools.neo4j_audit import get_neo4j_uri, get_neo4j_auth

    # Automatically uses audit instance if LIVE_AUDIT_MODE is set
    uri = get_neo4j_uri()
    auth = get_neo4j_auth()
"""

import os


def get_neo4j_uri() -> str:
    """
    Get Neo4j URI based on execution context.

    Returns:
        - bolt://localhost:7688 if LIVE_AUDIT_MODE env var is set (audit instance)
        - bolt://localhost:7687 otherwise (MCP instance)
    """
    if os.getenv("LIVE_AUDIT_MODE"):
        # Audit instance: higher memory (1024m), port 7688
        return "bolt://localhost:7688"
    else:
        # MCP instance: standard port 7687
        return "bolt://localhost:7687"


def get_neo4j_auth() -> tuple[str, str]:
    """
    Get Neo4j credentials based on execution context.

    Returns:
        Tuple of (username, password)

    Raises:
        RuntimeError: If password is not set in environment.
    """
    if os.getenv("LIVE_AUDIT_MODE"):
        # Audit instance has separate credentials
        password = os.getenv("NEO4J_AUDIT_PASSWORD")
        if not password:
            raise RuntimeError("NEO4J_AUDIT_PASSWORD environment variable is not set")
        return ("neo4j", password)
    else:
        # MCP instance
        password = os.getenv("NEO4J_PASSWORD")
        if not password:
            raise RuntimeError("NEO4J_PASSWORD environment variable is not set")
        return ("neo4j", password)


def is_audit_mode() -> bool:
    """Check if running in audit mode."""
    return bool(os.getenv("LIVE_AUDIT_MODE"))


def get_heap_info() -> str:
    """Get current Neo4j heap configuration."""
    if is_audit_mode():
        return "Neo4j Audit (1024m heap, 2g container limit)"
    else:
        return "Neo4j MCP (256m heap, 1g container limit)"
