#!/usr/bin/env python3
"""
MCP Neo4j Server
Part of Tessellae - tools for knowledge work

Exposes Neo4j graph database via Model Context Protocol.
Query Neo4j directly from Claude Desktop or any MCP client.
"""

import asyncio
import json
import sys
from typing import Any
from neo4j import GraphDatabase
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


class Neo4jMCPServer:
    """MCP Server for Neo4j graph database queries"""
    
    def __init__(self, uri: str, username: str, password: str):
        self.uri = uri
        self.username = username
        self.password = password
        self.driver = None
        
    def connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            # Test connection
            self.driver.verify_connectivity()
            print(f"✓ Connected to Neo4j at {self.uri}", file=sys.stderr)
        except Exception as e:
            print(f"✗ Failed to connect to Neo4j: {e}", file=sys.stderr)
            raise
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
    
    def execute_cypher(self, query: str, parameters: dict = None) -> list[dict]:
        """Execute a Cypher query and return results"""
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j")
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                # Convert result to list of dicts
                records = []
                for record in result:
                    records.append(dict(record))
                return records
        except Exception as e:
            raise RuntimeError(f"Cypher query failed: {e}")


async def main():
    """Main MCP server entry point"""
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python server.py <neo4j_uri> [--username <user>] [--password <pass>]", file=sys.stderr)
        sys.exit(1)
    
    uri = sys.argv[1]
    username = "neo4j"
    password = ""
    
    # Parse optional args
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--username" and i + 1 < len(sys.argv):
            username = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--password" and i + 1 < len(sys.argv):
            password = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    # Create Neo4j server
    neo4j_server = Neo4jMCPServer(uri, username, password)
    neo4j_server.connect()
    
    # Create MCP server
    server = Server("mcp-neo4j")
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available Neo4j tools"""
        return [
            Tool(
                name="cypher_query",
                description="Execute a read-only Cypher query on the Neo4j graph database. Returns nodes, relationships, and properties as JSON.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Cypher query to execute (read-only, no WRITE operations)"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Optional query parameters (e.g., {'name': 'Alice'})",
                            "default": {}
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="get_schema",
                description="Get the Neo4j database schema including node labels, relationship types, and property keys",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Any) -> list[TextContent]:
        """Handle tool calls"""
        
        if name == "cypher_query":
            query = arguments.get("query", "")
            parameters = arguments.get("parameters", {})
            
            # Security: Prevent write operations
            query_upper = query.upper().strip()
            forbidden = ["CREATE", "DELETE", "SET", "REMOVE", "MERGE", "DROP", "DETACH"]
            if any(query_upper.startswith(op) for op in forbidden):
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "Write operations are not allowed. Only READ queries (MATCH, RETURN, etc.)"
                    })
                )]
            
            try:
                results = neo4j_server.execute_cypher(query, parameters)
                return [TextContent(
                    type="text",
                    text=json.dumps(results, indent=2, default=str)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)})
                )]
        
        elif name == "get_schema":
            try:
                # Get node labels
                labels_query = "CALL db.labels()"
                labels = neo4j_server.execute_cypher(labels_query)
                
                # Get relationship types
                rels_query = "CALL db.relationshipTypes()"
                rels = neo4j_server.execute_cypher(rels_query)
                
                # Get property keys
                props_query = "CALL db.propertyKeys()"
                props = neo4j_server.execute_cypher(props_query)
                
                schema = {
                    "node_labels": [r['label'] for r in labels],
                    "relationship_types": [r['relationshipType'] for r in rels],
                    "property_keys": [r['propertyKey'] for r in props]
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(schema, indent=2)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)})
                )]
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]
    
    # Run server
    try:
        async with stdio_server() as (read_stream, write_stream):
            print("MCP Neo4j Server running...", file=sys.stderr)
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        neo4j_server.close()


if __name__ == "__main__":
    asyncio.run(main())
