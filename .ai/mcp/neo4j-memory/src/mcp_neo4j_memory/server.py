"""MCP server implementation"""

import logging
from typing import Any
from fastmcp import FastMCP

from .neo4j_connection import Neo4jConnection, Neo4jSettings
from .memory_manager import Neo4jMemoryManager, MemoryProfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("neo4j-memory", "1.0.0")

_neo4j_conn: Neo4jConnection | None = None
_memory_manager: Neo4jMemoryManager | None = None


def get_neo4j_connection() -> Neo4jConnection:
    """Get or create Neo4j connection"""
    global _neo4j_conn
    if _neo4j_conn is None:
        settings = Neo4jSettings()
        _neo4j_conn = Neo4jConnection(settings)
        _neo4j_conn.connect()
    return _neo4j_conn


def get_memory_manager() -> Neo4jMemoryManager:
    """Get or create memory manager"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = Neo4jMemoryManager()
    return _memory_manager


@mcp.tool()
def get_memory_profile(profile_name: str) -> dict[str, Any]:
    """Get a memory profile by name"""
    manager = get_memory_manager()
    profile = manager.get_profile(profile_name)
    if not profile:
        return {"error": f"Profile '{profile_name}' not found"}
    return profile.to_dict()


@mcp.tool()
def list_memory_profiles() -> dict[str, dict[str, Any]]:
    """List all available memory profiles"""
    manager = get_memory_manager()
    profiles = manager.list_profiles()
    return {name: profile.to_dict() for name, profile in profiles.items()}


@mcp.tool()
def get_current_profile() -> dict[str, Any]:
    """Get the currently active memory profile"""
    manager = get_memory_manager()
    profile = manager.get_current_profile()
    if not profile:
        return {"error": "No current profile set"}
    return profile.to_dict()


@mcp.tool()
def set_memory_profile(profile_name: str) -> dict[str, str]:
    """Set the current memory profile"""
    manager = get_memory_manager()
    if manager.set_current_profile(profile_name):
        return {"success": "true", "message": f"Profile set to: {profile_name}"}
    return {"success": "false", "error": f"Profile '{profile_name}' not found"}


@mcp.tool()
def recommend_memory_configuration(available_ram_gb: float) -> dict[str, Any]:
    """Get memory configuration recommendations"""
    if available_ram_gb <= 0:
        return {"error": "available_ram_gb must be positive"}
    manager = get_memory_manager()
    return manager.recommend_configuration(available_ram_gb)


@mcp.tool()
def export_environment_variables(profile_name: str | None = None) -> dict[str, str]:
    """Export memory profile as environment variables"""
    manager = get_memory_manager()
    env_vars = manager.export_env_vars(profile_name)
    if not env_vars:
        return {"error": "Could not export environment variables"}
    return env_vars


@mcp.tool()
def save_custom_profile(
    name: str,
    description: str,
    heap_initial: str,
    heap_max: str,
    pagecache: str,
    transaction_max: str = "2g",
    global_tx_max: str = "20g",
    use_case: str = "Custom",
) -> dict[str, str]:
    """Save a custom memory profile"""
    manager = get_memory_manager()
    profile = MemoryProfile(
        name=name,
        description=description,
        heap_initial=heap_initial,
        heap_max=heap_max,
        pagecache=pagecache,
        transaction_max=transaction_max,
        global_tx_max=global_tx_max,
        use_case=use_case,
    )
    manager.save_profile(name, profile)
    return {"success": "true", "message": f"Profile '{name}' saved"}


@mcp.tool()
def check_neo4j_health() -> dict[str, Any]:
    """Check Neo4j server health"""
    conn = get_neo4j_connection()
    connected = conn.test_connection()
    if not connected:
        return {"connected": False, "error": "Failed to connect"}
    return {
        "connected": True,
        "server_info": conn.get_server_info(),
        "memory_config": conn.get_memory_config(),
        "memory_usage": conn.get_memory_usage(),
        "transactions": conn.get_transaction_stats(),
    }


@mcp.tool()
def get_memory_usage() -> dict[str, Any]:
    """Get current Neo4j memory usage"""
    conn = get_neo4j_connection()
    return conn.get_memory_usage()


@mcp.tool()
def get_transaction_statistics() -> dict[str, Any]:
    """Get Neo4j transaction statistics"""
    conn = get_neo4j_connection()
    return conn.get_transaction_stats()


@mcp.tool()
def get_database_statistics() -> dict[str, Any]:
    """Get Neo4j database statistics"""
    conn = get_neo4j_connection()
    return conn.get_database_stats()


@mcp.tool()
def get_troubleshooting_guide() -> dict[str, Any]:
    """Get troubleshooting guide"""
    manager = get_memory_manager()
    return manager.get_troubleshooting_guide()


def main():
    """Run the MCP server"""
    logger.info("Starting Neo4j Memory Management MCP Server")
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped")
    finally:
        if _neo4j_conn:
            _neo4j_conn.disconnect()
