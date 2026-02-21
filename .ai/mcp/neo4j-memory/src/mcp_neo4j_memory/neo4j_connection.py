"""Neo4j connection and utilities"""

from typing import Any, Optional
from neo4j import GraphDatabase, Session, AsyncSession
from pydantic_settings import BaseSettings


class Neo4jSettings(BaseSettings):
    """Neo4j connection settings"""

    url: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"
    encrypted: bool = True
    trust: str = "TRUST_ALL_CERTIFICATES"

    class Config:
        env_prefix = "NEO4J_"
        case_sensitive = False


class Neo4jConnection:
    """Neo4j connection manager"""

    def __init__(self, settings: Neo4jSettings):
        """Initialize Neo4j connection"""
        self.settings = settings
        self._driver = None

    def connect(self) -> None:
        """Connect to Neo4j"""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.settings.url,
                auth=(self.settings.username, self.settings.password),
                encrypted=self.settings.encrypted,
                trust=self.settings.trust,
            )

    def disconnect(self) -> None:
        """Disconnect from Neo4j"""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    @property
    def driver(self):
        """Get Neo4j driver"""
        if self._driver is None:
            self.connect()
        return self._driver

    def get_session(self) -> Session:
        """Get Neo4j session"""
        return self.driver.session(database=self.settings.database)

    async def get_async_session(self) -> AsyncSession:
        """Get async Neo4j session"""
        return self.driver.session(database=self.settings.database)

    def test_connection(self) -> bool:
        """Test connection to Neo4j"""
        try:
            with self.get_session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False

    def get_server_info(self) -> dict[str, Any]:
        """Get Neo4j server information"""
        try:
            with self.get_session() as session:
                result = session.run(
                    "CALL dbms.components() YIELD name, versions, edition "
                    "RETURN name, versions, edition"
                )
                records = list(result)
                if records:
                    record = records[0]
                    return {
                        "name": record["name"],
                        "versions": record["versions"],
                        "edition": record["edition"],
                    }
            return {"error": "Could not retrieve server info"}
        except Exception as e:
            return {"error": str(e)}

    def get_memory_config(self) -> dict[str, Any]:
        """Get Neo4j memory configuration"""
        try:
            with self.get_session() as session:
                result = session.run("CALL dbms.listConfig() YIELD name, value WHERE name CONTAINS 'memory' RETURN name, value ORDER BY name")
                configs = {}
                for record in result:
                    configs[record["name"]] = record["value"]
                return configs
        except Exception as e:
            return {"error": str(e)}

    def get_memory_usage(self) -> dict[str, Any]:
        """Get current memory usage"""
        try:
            with self.get_session() as session:
                # Query JVM memory info
                result = session.run(
                    "CALL java.lang.Runtime.getRuntime() YIELD result "
                    "RETURN result.totalMemory() as total, "
                    "result.freeMemory() as free, "
                    "result.maxMemory() as max"
                )
                record = result.single()
                if record:
                    total = record["total"]
                    free = record["free"]
                    used = total - free
                    max_mem = record["max"]
                    return {
                        "total_bytes": total,
                        "used_bytes": used,
                        "free_bytes": free,
                        "max_bytes": max_mem,
                        "used_percent": (used / max_mem * 100) if max_mem > 0 else 0,
                    }
            return {"error": "Could not retrieve memory usage"}
        except Exception as e:
            # Fallback if CALL java not available
            return {"error": str(e), "note": "Java interop may not be enabled"}

    def get_transaction_stats(self) -> dict[str, Any]:
        """Get transaction statistics"""
        try:
            with self.get_session() as session:
                result = session.run(
                    "SHOW TRANSACTIONS WHERE status = 'Running' "
                    "RETURN COUNT(*) as active_transactions, "
                    "AVG(age) as avg_age, "
                    "MAX(age) as max_age"
                )
                record = result.single()
                if record:
                    return {
                        "active_transactions": record["active_transactions"],
                        "avg_age_ms": record["avg_age"],
                        "max_age_ms": record["max_age"],
                    }
            return {"error": "Could not retrieve transaction stats"}
        except Exception as e:
            return {"error": str(e)}

    def get_database_stats(self) -> dict[str, Any]:
        """Get database statistics"""
        try:
            with self.get_session() as session:
                # Count nodes and relationships
                result = session.run(
                    "RETURN COUNT(DISTINCT (MATCH (n) RETURN n)) as nodes, "
                    "COUNT(DISTINCT (MATCH ()-[r]-() RETURN r)) as relationships"
                )
                # Simplified query
                nodes_result = session.run("MATCH (n) RETURN COUNT(n) as count")
                nodes_count = nodes_result.single()["count"] if nodes_result.single() else 0

                rels_result = session.run("MATCH ()-[r]-() RETURN COUNT(r) as count")
                rels_count = rels_result.single()["count"] if rels_result.single() else 0

                return {
                    "nodes": nodes_count,
                    "relationships": rels_count,
                }
        except Exception as e:
            return {"error": str(e)}
