# MCP Neo4j Server

**Model Context Protocol server for Neo4j graph databases**

Query Neo4j directly from Claude Desktop (or any MCP client) via Cypher queries. Built because the official `@modelcontextprotocol/server-neo4j` package didn't exist yet.

Part of [Tessellae](../) - open-source tools for knowledge work.

---

## Features

- 🔍 **Execute Cypher queries** - Read-only access to your graph
- 📊 **Get database schema** - Discover node labels, relationships, properties
- 🔒 **Security built-in** - Write operations blocked by default
- 🚀 **Fast & simple** - Direct Neo4j driver, no middleware
- 🐍 **Python-based** - Easy to customize and extend

---

## Quick Start

### Prerequisites

- Python 3.10+
- Neo4j database (local or remote)
- Claude Desktop

### Installation

```bash
# Clone the repository
git clone https://github.com/ontologue/tessellae.git
cd tessellae/mcp-neo4j

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Add to your Claude Desktop config file:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`  
**macOS/Linux:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "python",
      "args": [
        "/absolute/path/to/tessellae/mcp-neo4j/server.py",
        "bolt://localhost:7687",
        "--username",
        "neo4j",
        "--password",
        "your_password"
      ]
    }
  }
}
```

**Important:** Replace:
- Path to `server.py` with actual absolute path
- `your_password` with your Neo4j password
- Connection URI if not using default `bolt://localhost:7687`

### Restart Claude Desktop

Quit Claude Desktop completely and restart. The MCP server will start automatically in the background.

---

## Usage Examples

Once configured, you can ask Claude things like:

### Explore your graph
```
What's the structure of my Neo4j database?
```

Claude will call `get_schema` to retrieve node labels, relationship types, and properties.

### Query specific data
```
Find all entities related to "knowledge graph"
```

Claude will construct and execute an appropriate Cypher query:
```cypher
MATCH (e:Entity)-[r]-(connected)
WHERE e.name CONTAINS 'knowledge graph'
RETURN e, r, connected
LIMIT 50
```

### Complex queries
```
Show me the shortest path between concepts X and Y in my graph
```

Claude can construct multi-hop path queries and analyze the results.

---

## Available Tools

### `cypher_query`

Execute read-only Cypher queries.

**Parameters:**
- `query` (string, required): Cypher query to execute
- `parameters` (object, optional): Query parameters for parameterized queries

**Security:** Write operations (CREATE, DELETE, SET, MERGE, DROP) are blocked.

**Example:**
```cypher
MATCH (n:Person)-[:KNOWS]->(friend)
WHERE n.name = $name
RETURN friend.name, friend.age
```

### `get_schema`

Retrieve the database schema.

**Returns:**
- `node_labels`: Array of node labels in the database
- `relationship_types`: Array of relationship types
- `property_keys`: Array of property keys used

---

## Testing

Test the server manually before using with Claude:

```bash
python server.py bolt://localhost:7687 --username neo4j --password your_password
```

If successful, you'll see:
```
✓ Connected to Neo4j at bolt://localhost:7687
MCP Neo4j Server running...
```

Press `Ctrl+C` to stop. The server waits for MCP messages on stdin.

---

## Troubleshooting

### Server doesn't appear in Claude

**Check the logs:**
- **Windows:** `%APPDATA%\Claude\logs\mcp*.log`
- **macOS:** `~/Library/Logs/Claude/mcp*.log`

Look for error messages related to `neo4j`.

### Connection failed

**Verify Neo4j is running:**
```bash
# If using Docker
docker ps | grep neo4j

# If installed locally, check if service is running
```

**Test connection manually:**
```bash
python server.py bolt://localhost:7687 --username neo4j --password test
```

### Module not found errors

**Ensure dependencies are installed:**
```bash
pip install -r requirements.txt
```

**Check Python version:**
```bash
python --version  # Should be 3.10+
```

---

## Development

### Architecture

```
server.py
├── Neo4jMCPServer
│   ├── connect()       - Establish Neo4j connection
│   ├── execute_cypher() - Run Cypher queries
│   └── close()         - Clean up connection
│
└── MCP Server
    ├── list_tools()    - Expose available tools
    └── call_tool()     - Handle tool invocations
```

### Adding features

To add new capabilities:

1. Add a new tool in `list_tools()`
2. Handle it in `call_tool()`
3. Use `neo4j_server.execute_cypher()` for Neo4j access

### Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests if applicable
4. Submit a pull request

---

## Roadmap

Potential future features:

- [ ] Write operations (with user confirmation prompts)
- [ ] Query result pagination for large datasets
- [ ] Query caching and optimization hints
- [ ] Support for multiple Neo4j instances
- [ ] WebSocket support for real-time graph updates
- [ ] Graph visualization data export

---

## License

MIT License - See [LICENSE](../LICENSE)

---

## Credits

**Author:** Cyril Soler-Bonnet ([@ontologue](https://github.com/ontologue))

**Built with:**
- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)

**Inspired by:** The need for a working Neo4j MCP server when `@modelcontextprotocol/server-neo4j` didn't exist yet.

---

## See Also

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/docs)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/)
- [Claude Desktop](https://claude.ai/download)
- [Other Tessellae projects](../)

---

*Part of Tessellae - like tessellae forming a mosaic, tools that connect.*
