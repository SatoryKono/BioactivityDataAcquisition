"""
MCP Neo4j Memory Management Server

A Model Context Protocol server for managing and optimizing Neo4j memory configuration
for the BioETL project.

Usage:
    from .ai.mcp.neo4j_memory.server import Neo4jMemoryMCP
    
    mcp = Neo4jMemoryMCP()
    rec = mcp.recommend_configuration(8)  # 8GB host RAM
"""

__version__ = "1.0.0"
__author__ = "BioETL"
__description__ = "MCP Server for Neo4j Memory Management"

from .server import Neo4jMemoryMCP

__all__ = ["Neo4jMemoryMCP"]
