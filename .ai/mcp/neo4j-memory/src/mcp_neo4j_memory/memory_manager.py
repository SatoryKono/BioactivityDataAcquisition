"""Neo4j memory management"""

from dataclasses import dataclass
from typing import Any
import json
from pathlib import Path
from datetime import datetime


@dataclass
class MemoryProfile:
    """Memory profile configuration"""

    name: str
    description: str
    heap_initial: str
    heap_max: str
    pagecache: str
    transaction_max: str
    global_tx_max: str
    use_case: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "heap_initial": self.heap_initial,
            "heap_max": self.heap_max,
            "pagecache": self.pagecache,
            "transaction_max": self.transaction_max,
            "global_tx_max": self.global_tx_max,
            "use_case": self.use_case,
        }


class Neo4jMemoryManager:
    """Neo4j memory management"""

    PROFILES = {
        "development": MemoryProfile(
            name="development",
            description="Development environment (4GB host RAM)",
            heap_initial="512m",
            heap_max="2g",
            pagecache="1g",
            transaction_max="2g",
            global_tx_max="20g",
            use_case="Local development, small datasets",
        ),
        "staging": MemoryProfile(
            name="staging",
            description="Staging environment (8GB host RAM)",
            heap_initial="1g",
            heap_max="4g",
            pagecache="2g",
            transaction_max="4g",
            global_tx_max="30g",
            use_case="Testing, medium datasets",
        ),
        "production": MemoryProfile(
            name="production",
            description="Production environment (16GB+ host RAM)",
            heap_initial="2g",
            heap_max="8g",
            pagecache="6g",
            transaction_max="8g",
            global_tx_max="50g",
            use_case="High throughput, large datasets",
        ),
    }

    def __init__(self, storage_path: str = ".ai/mcp/neo4j-memory/memory.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.custom_profiles: dict[str, MemoryProfile] = {}
        self.current_profile = "development"
        self._load_storage()

    def _load_storage(self) -> None:
        """Load configuration from storage"""
        if self.storage_path.exists():
            with open(self.storage_path) as f:
                data = json.load(f)
                self.current_profile = data.get("current_profile", "development")
                if "custom_profiles" in data:
                    for name, config in data["custom_profiles"].items():
                        self.custom_profiles[name] = MemoryProfile(
                            name=name,
                            description=config.get("description", ""),
                            heap_initial=config["heap_initial"],
                            heap_max=config["heap_max"],
                            pagecache=config["pagecache"],
                            transaction_max=config.get("transaction_max", "2g"),
                            global_tx_max=config.get("global_tx_max", "20g"),
                            use_case=config.get("use_case", ""),
                        )

    def _save_storage(self) -> None:
        """Save configuration to storage"""
        data = {
            "current_profile": self.current_profile,
            "last_updated": datetime.now().isoformat(),
            "custom_profiles": {
                name: {
                    "description": profile.description,
                    "heap_initial": profile.heap_initial,
                    "heap_max": profile.heap_max,
                    "pagecache": profile.pagecache,
                    "transaction_max": profile.transaction_max,
                    "global_tx_max": profile.global_tx_max,
                    "use_case": profile.use_case,
                }
                for name, profile in self.custom_profiles.items()
            },
        }
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_profile(self, name: str) -> MemoryProfile | None:
        """Get a memory profile"""
        if name in self.PROFILES:
            return self.PROFILES[name]
        return self.custom_profiles.get(name)

    def list_profiles(self) -> dict[str, MemoryProfile]:
        """List all available profiles"""
        return {**self.PROFILES, **self.custom_profiles}

    def get_current_profile(self) -> MemoryProfile | None:
        """Get current profile"""
        return self.get_profile(self.current_profile)

    def set_current_profile(self, name: str) -> bool:
        """Set current profile"""
        if self.get_profile(name):
            self.current_profile = name
            self._save_storage()
            return True
        return False

    def save_profile(self, name: str, profile: MemoryProfile) -> None:
        """Save custom profile"""
        self.custom_profiles[name] = profile
        self._save_storage()

    def recommend_configuration(self, available_ram_gb: float) -> dict[str, Any]:
        """Recommend configuration based on available RAM"""
        heap_max = int(available_ram_gb * 0.35)
        heap_initial = max(1, int(available_ram_gb * 0.1))
        pagecache = int(available_ram_gb * 0.45)

        return {
            "available_ram_gb": available_ram_gb,
            "heap_initial": f"{heap_initial}g",
            "heap_max": f"{heap_max}g",
            "pagecache": f"{pagecache}g",
            "allocation": {"heap": "35%", "pagecache": "45%", "os": "20%"},
        }

    def export_env_vars(self, profile_name: str | None = None) -> dict[str, str]:
        """Export profile as environment variables"""
        profile = self.get_profile(profile_name or self.current_profile)
        if not profile:
            return {}

        return {
            "NEO4J_HEAP_INITIAL": profile.heap_initial,
            "NEO4J_HEAP_MAX": profile.heap_max,
            "NEO4J_PAGECACHE": profile.pagecache,
            "NEO4J_TX_MAX_SIZE": profile.transaction_max,
            "NEO4J_GLOBAL_TX_MAX": profile.global_tx_max,
        }

    def get_troubleshooting_guide(self) -> dict[str, Any]:
        """Get troubleshooting guide"""
        return {
            "out_of_memory": {
                "cause": "heap + pagecache exceeds available RAM",
                "solution": "Reduce heap or pagecache, ensure total <= 80% RAM",
            },
            "slow_queries": {
                "cause": "Insufficient page cache",
                "solution": "Increase NEO4J_PAGECACHE",
            },
        }
