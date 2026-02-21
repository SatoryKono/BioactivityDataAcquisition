"""MCP server implementation for Neo4j memory management"""

import logging
from typing import Any
from fastmcp import FastMCP
from pydantic import BaseModel

from .neo4j_connection import Neo4jConnection, Neo4jSettings
from .memory_manager import Neo4jMemoryManager, MemoryProfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryRecommendation(BaseModel):
    """Memory recommendation response"""

    available_ram_gb: float
    heap_initial: str
    heap_max: str
    pagecache: str
    os_reserve: str
    allocation_percentages: dict[str, str]
    rationale: str


class ProfileInfo(BaseModel):
    """Memory profile information"""

    name: str
    description: str
    heap_initial: str
    heap_max: str
    pagecache: str
    transaction_max: str
    global_tx_max: str
    use_case: str


class HealthStatus(BaseModel):
    """Neo4j health status"""

    connected: bool
    server_info: dict[str, Any]
    memory_config: dict[str, Any]
    memory_usage: dict[str, Any]
    transactions: dict[str, Any]
    database_stats: dict[str, Any]


# Initialize MCP server
mcp = FastMCP("neo4j-memory", "1.0.0")

# Global instances
_neo4j_conn: Neo4jConnection | None = None
_memory_manager: Neo4jMemoryManager | None = None


def get_neo4j_connection() -> Neo4jConnection:
    """Get or create Neo4j connection"""
    global _neo4j_conn
    if _neo4j_conn is None:
        settings = Neo4jSettings()
        _neo4j_conn = Neo4jConnection(settings)
        _neo4j_conn.connect()
        logger.info(f"Connected to Neo4j at {settings.url}")
    return _neo4j_conn


def get_memory_manager() -> Neo4jMemoryManager:
    """Get or create memory manager"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = Neo4jMemoryManager()
        logger.info("Memory manager initialized")
    return _memory_manager


@mcp.tool()
def get_memory_profile(profile_name: str) -> dict[str, Any]:
    """Get a memory profile by name

    Args:
        profile_name: Name of the profile (development, staging, production, or custom)

    Returns:
        Profile configuration details
    """
    manager = get_memory_manager()
    profile = manager.get_profile(profile_name)

    if not profile:
        return {"error": f"Profile '{profile_name}' not found"}

    return profile.to_dict()


@mcp.tool()
def list_memory_profiles() -> dict[str, dict[str, Any]]:
    """List all available memory profiles

    Returns:
        Dictionary of all profiles
    """
    manager = get_memory_manager()
    profiles = manager.list_profiles()
    return {name: profile.to_dict() for name, profile in profiles.items()}


@mcp.tool()
def get_current_profile() -> dict[str, Any]:
    """Get the currently active memory profile

    Returns:
        Current profile configuration
    """
    manager = get_memory_manager()
    profile = manager.get_current_profile()

    if not profile:
        return {"error": "No current profile set"}

    return profile.to_dict()


@mcp.tool()
def set_memory_profile(profile_name: str) -> dict[str, str]:
    """Set the current memory profile

    Args:
        profile_name: Name of the profile to activate

    Returns:
        Confirmation message
    """
    manager = get_memory_manager()

    if manager.set_current_profile(profile_name):
        return {
            "success": "true",
            "message": f"Memory profile set to: {profile_name}",
            "profile": profile_name,
        }

    return {"success": "false", "error": f"Profile '{profile_name}' not found"}


@mcp.tool()
def recommend_memory_configuration(available_ram_gb: float) -> dict[str, Any]:
    """Get memory configuration recommendations based on available host RAM

    Args:
        available_ram_gb: Available host RAM in gigabytes

    Returns:
        Recommended memory configuration
    """
    if available_ram_gb <= 0:
        return {"error": "available_ram_gb must be positive"}

    manager = get_memory_manager()
    return manager.recommend_configuration(available_ram_gb)


@mcp.tool()
def export_environment_variables(profile_name: str | None = None) -> dict[str, str]:
    """Export memory profile as environment variables

    Args:
        profile_name: Profile name (uses current if not specified)

    Returns:
        Environment variables for the profile
    """
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
    """Save a custom memory profile

    Args:
        name: Profile name
        description: Profile description
        heap_initial: Initial heap size
        heap_max: Maximum heap size
        pagecache: Page cache size
        transaction_max: Single transaction max
        global_tx_max: Global transaction limit
        use_case: Use case description

    Returns:
        Confirmation message
    """
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
    return {
        "success": "true",
        "message": f"Custom profile '{name}' saved successfully",
    }


@mcp.tool()
def check_neo4j_health() -> dict[str, Any]:
    """Check Neo4j server health and memory status

    Returns:
        Health status with server info, memory usage, and transaction stats
    """
    conn = get_neo4j_connection()

    connected = conn.test_connection()
    if not connected:
        return {
            "connected": False,
            "error": "Failed to connect to Neo4j",
        }

    return {
        "connected": True,
        "server_info": conn.get_server_info(),
        "memory_config": conn.get_memory_config(),
        "memory_usage": conn.get_memory_usage(),
        "transactions": conn.get_transaction_stats(),
        "database_stats": conn.get_database_stats(),
    }


@mcp.tool()
def get_memory_usage() -> dict[str, Any]:
    """Get current Neo4j memory usage

    Returns:
        Memory usage statistics
    """
    conn = get_neo4j_connection()
    return conn.get_memory_usage()


@mcp.tool()
def get_transaction_statistics() -> dict[str, Any]:
    """Get Neo4j transaction statistics

    Returns:
        Transaction statistics
    """
    conn = get_neo4j_connection()
    return conn.get_transaction_stats()


@mcp.tool()
def get_database_statistics() -> dict[str, Any]:
    """Get Neo4j database statistics

    Returns:
        Database statistics (node count, relationship count)
    """
    conn = get_neo4j_connection()
    return conn.get_database_stats()


@mcp.tool()
def get_troubleshooting_guide() -> dict[str, Any]:
    """Get troubleshooting guide for common Neo4j memory issues

    Returns:
        Troubleshooting guide with symptoms, causes, and solutions
    """
    manager = get_memory_manager()
    return manager.get_troubleshooting_guide()


def main():
    """Run the MCP server"""
    logger.info("Starting Neo4j Memory Management MCP Server")
    logger.info("Available tools:")
    logger.info("  - get_memory_profile")
    logger.info("  - list_memory_profiles")
    logger.info("  - get_current_profile")
    logger.info("  - set_memory_profile")
    logger.info("  - recommend_memory_configuration")
    logger.info("  - export_environment_variables")
    logger.info("  - save_custom_profile")
    logger.info("  - check_neo4j_health")
    logger.info("  - get_memory_usage")
    logger.info("  - get_transaction_statistics")
    logger.info("  - get_database_statistics")
    logger.info("  - get_troubleshooting_guide")

    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise
    finally:
        if _neo4j_conn:
            _neo4j_conn.disconnect()
            logger.info("Disconnected from Neo4j")


if __name__ == "__main__":
    main()
