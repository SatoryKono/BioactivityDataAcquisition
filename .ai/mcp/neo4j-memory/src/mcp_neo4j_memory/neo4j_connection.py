"""Neo4j connection management"""

from typing import Any
from neo4j import GraphDatabase, Session
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
                result = session.run(
                    "CALL dbms.listConfig() YIELD name, value "
                    "WHERE name CONTAINS 'memory' "
                    "RETURN name, value ORDER BY name"
                )
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
                result = session.run("SHOW DATABASES YIELD name RETURN name")
                return {"databases": [r["name"] for r in result]}
        except Exception as e:
            return {"error": str(e)}

    def get_transaction_stats(self) -> dict[str, Any]:
        """Get transaction statistics"""
        try:
            with self.get_session() as session:
                result = session.run("SHOW TRANSACTIONS YIELD id RETURN COUNT(*) as count")
                count = result.single()["count"] if result.single() else 0
                return {"active_transactions": count}
        except Exception as e:
            return {"error": str(e)}

    def get_database_stats(self) -> dict[str, Any]:
        """Get database statistics"""
        try:
            with self.get_session() as session:
                nodes_result = session.run("MATCH (n) RETURN COUNT(n) as count")
                nodes = nodes_result.single()["count"] if nodes_result.single() else 0
                return {"nodes": nodes}
        except Exception as e:
            return {"error": str(e)}
