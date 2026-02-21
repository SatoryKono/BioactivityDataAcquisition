#!/usr/bin/env python3
"""
MCP Server for Neo4j Memory Management
Provides tools for monitoring and optimizing Neo4j memory configuration
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class Neo4jMemoryMCP:
    """MCP server for Neo4j memory management"""

    def __init__(self, memory_file_path: str = ".ai/mcp/neo4j-memory/memory.json"):
        """Initialize the MCP server"""
        self.memory_file = Path(memory_file_path)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.memory_file.exists():
            self._init_memory_store()
        else:
            self.memory = self._load_memory()

    def _init_memory_store(self) -> None:
        """Initialize the memory storage file"""
        initial_memory = {
            "project_info": {
                "name": "BioETL Neo4j Memory Management",
                "description": "Neo4j memory configuration and tuning for graph database",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
            },
            "memory_profiles": {
                "development": {
                    "description": "Development environment (4GB host RAM)",
                    "heap_initial": "512m",
                    "heap_max": "2g",
                    "pagecache": "1g",
                    "transaction_max": "2g",
                    "global_tx_max": "20g",
                    "use_case": "Local development, small datasets",
                },
                "staging": {
                    "description": "Staging environment (8GB host RAM)",
                    "heap_initial": "1g",
                    "heap_max": "4g",
                    "pagecache": "2g",
                    "transaction_max": "4g",
                    "global_tx_max": "30g",
                    "use_case": "Testing, medium datasets",
                },
                "production": {
                    "description": "Production environment (16GB+ host RAM)",
                    "heap_initial": "2g",
                    "heap_max": "8g",
                    "pagecache": "6g",
                    "transaction_max": "8g",
                    "global_tx_max": "50g",
                    "use_case": "High throughput, large datasets",
                },
            },
            "current_configuration": {
                "environment": "development",
                "heap_initial": "512m",
                "heap_max": "2g",
                "pagecache": "1g",
                "transaction_max_size": "2g",
                "global_transaction_max": "20g",
                "jvm_opts": "-XX:+UseG1GC -XX:G1HeapRegionSize=16m",
            },
            "memory_allocation_rules": {
                "heap_percentage": "25-40% of available host RAM",
                "pagecache_percentage": "40-50% of available host RAM",
                "os_buffer_reserve": "10-20% of available host RAM",
                "rationale": "Optimal balance between JVM heap, graph storage caching, and OS buffer",
            },
            "custom_configurations": {},
        }
        self.memory = initial_memory
        self._save_memory()

    def _load_memory(self) -> dict:
        """Load memory from file"""
        with open(self.memory_file) as f:
            return json.load(f)

    def _save_memory(self) -> None:
        """Save memory to file"""
        self.memory["last_updated"] = datetime.now().isoformat()
        with open(self.memory_file, "w") as f:
            json.dump(self.memory, f, indent=2)

    def get_memory_profile(self, profile: str) -> dict:
        """Get a memory profile"""
        if profile not in self.memory["memory_profiles"]:
            return {"error": f"Profile '{profile}' not found"}
        return self.memory["memory_profiles"][profile]

    def get_current_configuration(self) -> dict:
        """Get current configuration"""
        return self.memory["current_configuration"]

    def get_memory_allocation_rules(self) -> dict:
        """Get memory allocation rules"""
        return self.memory["memory_allocation_rules"]

    def check_neo4j_health(self) -> dict:
        """Check Neo4j container health"""
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "neo4j", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if not result.stdout.strip():
                return {
                    "status": "not_running",
                    "message": "Neo4j container not found. Start with: docker compose up -d neo4j",
                }

            try:
                containers = json.loads(result.stdout)
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "message": f"Could not parse Docker output",
                }

            if not containers:
                return {
                    "status": "not_running",
                    "message": "Neo4j container not found",
                }

            neo4j = containers[0]
            status_info = {
                "container_name": neo4j.get("Service", "neo4j"),
                "status": neo4j.get("State", "unknown"),
                "health": neo4j.get("Health", "N/A"),
            }

            try:
                stats_result = subprocess.run(
                    [
                        "docker",
                        "stats",
                        "bioetl-neo4j",
                        "--no-stream",
                        "--format",
                        "json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if stats_result.stdout.strip():
                    stats = json.loads(stats_result.stdout)[0]
                    status_info.update(
                        {
                            "memory_usage": stats.get("MemUsage", "N/A"),
                            "memory_percent": stats.get("MemPerc", "N/A"),
                            "cpu_percent": stats.get("CPUPerc", "N/A"),
                        }
                    )
            except Exception:
                pass

            return status_info
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "Docker command timed out"}
        except Exception as e:
            return {"status": "error", "message": f"Error: {str(e)}"}

    def recommend_configuration(self, available_ram_gb: float) -> dict:
        """Recommend configuration based on available RAM"""
        heap_max = int(available_ram_gb * 0.35)
        heap_initial = int(available_ram_gb * 0.1)
        pagecache = int(available_ram_gb * 0.45)
        os_reserve = int(available_ram_gb * 0.1)

        return {
            "available_ram_gb": available_ram_gb,
            "recommendation": f"Based on {available_ram_gb}GB available RAM",
            "heap_initial": f"{heap_initial}g",
            "heap_max": f"{heap_max}g",
            "pagecache": f"{pagecache}g",
            "os_reserve": f"{os_reserve}g",
            "allocation_percentages": {
                "heap": "35%",
                "pagecache": "45%",
                "os_reserve": "20%",
            },
            "rationale": "Heap 35%, PageCache 45%, OS Reserve 20% allocation",
        }

    def update_memory_profile(self, profile: str) -> dict:
        """Update to a memory profile"""
        if profile not in self.memory["memory_profiles"]:
            return {"error": f"Profile '{profile}' not found"}

        self.memory["current_configuration"].update(
            {"environment": profile, **self.memory["memory_profiles"][profile]}
        )
        self._save_memory()
        return {"success": True, "message": f"Memory profile updated to: {profile}"}

    def save_custom_configuration(
        self, name: str, heap_initial: str, heap_max: str, pagecache: str
    ) -> dict:
        """Save a custom configuration"""
        self.memory["custom_configurations"][name] = {
            "heap_initial": heap_initial,
            "heap_max": heap_max,
            "pagecache": pagecache,
            "created_at": datetime.now().isoformat(),
        }
        self._save_memory()
        return {"success": True, "message": f"Custom configuration '{name}' saved"}

    def get_all_configurations(self) -> dict:
        """Get all configurations (builtin and custom)"""
        return {
            "profiles": self.memory["memory_profiles"],
            "custom_configurations": self.memory["custom_configurations"],
            "current": self.memory["current_configuration"],
        }

    def export_env_file(self, profile: str = None) -> str:
        """Export configuration as .env snippet"""
        if profile:
            config = self.get_memory_profile(profile)
        else:
            config = self.get_current_configuration()

        env_vars = [
            f"NEO4J_HEAP_INITIAL={config.get('heap_initial', '512m')}",
            f"NEO4J_HEAP_MAX={config.get('heap_max', '2g')}",
            f"NEO4J_PAGECACHE={config.get('pagecache', '1g')}",
            f"NEO4J_TX_MAX_SIZE={config.get('transaction_max', '2g')}",
            f"NEO4J_GLOBAL_TX_MAX={config.get('global_tx_max', '20g')}",
        ]
        return "\n".join(env_vars)

    def get_troubleshooting_guide(self) -> dict:
        """Get troubleshooting guide for common issues"""
        return {
            "out_of_memory": {
                "symptom": "Container exits with code 137 (OOM kill)",
                "cause": "heap + pagecache > available host RAM",
                "solution": [
                    "Check host RAM: free -h (Linux) or wmic (Windows)",
                    "Reduce NEO4J_HEAP_MAX",
                    "Reduce NEO4J_PAGECACHE",
                    "Ensure total <= 80% of host RAM",
                ],
                "command": "docker stats bioetl-neo4j",
            },
            "slow_queries": {
                "symptom": "Query performance degrades over time",
                "cause": "Insufficient page cache or GC pauses",
                "solution": [
                    "Increase NEO4J_PAGECACHE",
                    "Enable G1GC with NEO4J_JVM_OPTS",
                    "Profile with: cypher-shell 'PROFILE <query>'",
                ],
            },
            "transaction_timeout": {
                "symptom": "Transactions fail with timeout errors",
                "cause": "NEO4J_TX_MAX_SIZE too small",
                "solution": [
                    "Increase NEO4J_TX_MAX_SIZE",
                    "Batch large operations",
                    "Use indexes for frequent queries",
                ],
            },
        }


def main():
    """Main entry point"""
    memory_file = os.getenv(
        "MEMORY_FILE_PATH", ".ai/mcp/neo4j-memory/memory.json"
    )
    mcp = Neo4jMemoryMCP(memory_file)

    print("Neo4j Memory Management MCP Server")
    print("=" * 50)
    print(f"Memory file: {memory_file}\n")

    print("Current Configuration:")
    print(json.dumps(mcp.get_current_configuration(), indent=2))
    print()

    print("Available Profiles:")
    for profile_name in mcp.memory["memory_profiles"]:
        print(f"  - {profile_name}")
    print()

    print("Neo4j Health Status:")
    health = mcp.check_neo4j_health()
    print(json.dumps(health, indent=2))
    print()

    print("Recommendation for 8GB Host RAM:")
    recommendation = mcp.recommend_configuration(8)
    print(json.dumps(recommendation, indent=2))


if __name__ == "__main__":
    main()
