import json
import os
import psycopg2
import psycopg2.extras
from pathlib import Path
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

load_dotenv()

app = Server("postgres-server")

def get_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        database=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD")
    )

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="execute_query",
            description="Execute a SQL SELECT query against the Olist PostgreSQL database. Only SELECT allowed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The SQL SELECT query to execute"
                    }
                },
                "required": ["sql"]
            }
        ),
        Tool(
            name="list_tables",
            description="List all available tables in the database",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="describe_table",
            description="Get the schema of a specific table — column names and types",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to describe"
                    }
                },
                "required": ["table_name"]
            }
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if name == "list_tables":
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row["table_name"] for row in cursor.fetchall()]
            return [TextContent(type="text", text=json.dumps(tables))]

        elif name == "describe_table":
            table_name = arguments["table_name"]
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            columns = [
                {"name": row["column_name"], "type": row["data_type"]}
                for row in cursor.fetchall()
            ]
            return [TextContent(type="text", text=json.dumps(columns))]

        elif name == "execute_query":
            sql = arguments["sql"].strip()

            # Security: only SELECT allowed
            if not sql.upper().startswith("SELECT"):
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "Only SELECT statements are allowed"})
                )]

            cursor.execute(sql)
            rows = cursor.fetchmany(500)  # cap at 500 rows
            result = [dict(row) for row in rows]
            return [TextContent(type="text", text=json.dumps(result, default=str))]

        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    finally:
        cursor.close()
        conn.close()

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())