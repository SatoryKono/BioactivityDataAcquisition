"""
MCP Neo4j Memory - Usage Examples
=================================

Examples of how to use the Neo4j Memory Management MCP server
"""

from pathlib import Path
import sys
import json

# Add the MCP server to path
sys.path.insert(0, str(Path(".ai/mcp/neo4j-memory")))
from server import Neo4jMemoryMCP


def example_1_basic_usage():
    """Example 1: Basic usage"""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)

    mcp = Neo4jMemoryMCP()

    # Get current config
    current = mcp.get_current_configuration()
    print("Current Configuration:")
    print(json.dumps(current, indent=2))


def example_2_get_profile():
    """Example 2: Get a specific profile"""
    print("\n" + "=" * 60)
    print("Example 2: Get Profile (Staging)")
    print("=" * 60)

    mcp = Neo4jMemoryMCP()
    profile = mcp.get_memory_profile("staging")
    print(json.dumps(profile, indent=2))


def example_3_recommendation():
    """Example 3: Get recommendation for host RAM"""
    print("\n" + "=" * 60)
    print("Example 3: Recommendations")
    print("=" * 60)

    mcp = Neo4jMemoryMCP()

    for ram_gb in [4, 8, 16, 32]:
        print(f"\nFor {ram_gb}GB host RAM:")
        rec = mcp.recommend_configuration(ram_gb)
        print(f"  Heap: {rec['heap_initial']} -> {rec['heap_max']}")
        print(f"  PageCache: {rec['pagecache']}")
        print(f"  OS Reserve: {rec['os_reserve']}")


def example_4_export_env():
    """Example 4: Export as environment variables"""
    print("\n" + "=" * 60)
    print("Example 4: Export as .env")
    print("=" * 60)

    mcp = Neo4jMemoryMCP()

    for profile in ["development", "staging", "production"]:
        print(f"\n{profile.upper()}:")
        env = mcp.export_env_file(profile)
        print(env)


def example_5_custom_config():
    """Example 5: Save custom configuration"""
    print("\n" + "=" * 60)
    print("Example 5: Custom Configuration")
    print("=" * 60)

    mcp = Neo4jMemoryMCP()

    # Save custom config
    result = mcp.save_custom_configuration(
        name="high-memory",
        heap_initial="4g",
        heap_max="16g",
        pagecache="8g"
    )
    print(result["message"])

    # Get all configs
    all_configs = mcp.get_all_configurations()
    print("\nCustom Configurations:")
    for name, config in all_configs["custom_configurations"].items():
        print(f"  {name}:")
        print(f"    Heap: {config['heap_initial']} -> {config['heap_max']}")
        print(f"    PageCache: {config['pagecache']}")


def example_6_update_profile():
    """Example 6: Update current profile"""
    print("\n" + "=" * 60)
    print("Example 6: Update Profile")
    print("=" * 60)

    mcp = Neo4jMemoryMCP()

    print("Before:", mcp.get_current_configuration()["environment"])
    mcp.update_memory_profile("production")
    print("After:", mcp.get_current_configuration()["environment"])

    # Reset to development
    mcp.update_memory_profile("development")


def example_7_troubleshooting():
    """Example 7: Get troubleshooting guide"""
    print("\n" + "=" * 60)
    print("Example 7: Troubleshooting Guide")
    print("=" * 60)

    mcp = Neo4jMemoryMCP()
    guide = mcp.get_troubleshooting_guide()

    for issue, details in guide.items():
        print(f"\n{issue.upper().replace('_', ' ')}:")
        print(f"  Symptom: {details['symptom']}")
        print(f"  Cause: {details['cause']}")
        print(f"  Solutions:")
        for sol in details["solution"]:
            print(f"    - {sol}")


def example_8_allocation_rules():
    """Example 8: Memory allocation rules"""
    print("\n" + "=" * 60)
    print("Example 8: Memory Allocation Rules")
    print("=" * 60)

    mcp = Neo4jMemoryMCP()
    rules = mcp.get_memory_allocation_rules()

    print(json.dumps(rules, indent=2))


def example_9_health_check():
    """Example 9: Check Neo4j health"""
    print("\n" + "=" * 60)
    print("Example 9: Health Check")
    print("=" * 60)

    mcp = Neo4jMemoryMCP()
    health = mcp.check_neo4j_health()

    print(json.dumps(health, indent=2))


def run_all_examples():
    """Run all examples"""
    example_1_basic_usage()
    example_2_get_profile()
    example_3_recommendation()
    example_4_export_env()
    example_5_custom_config()
    example_6_update_profile()
    example_7_troubleshooting()
    example_8_allocation_rules()
    example_9_health_check()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_examples()
