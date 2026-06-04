import json
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _call_mcp_tool(server_script: str, tool_name: str, arguments: dict) -> dict:
    server = StdioServerParameters(command="python", args=[server_script])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            text = result.content[0].text
            return json.loads(text)


class MCPClient:

    # PostgreSQL server
    def execute_query(self, sql: str) -> dict:
        return _run(_call_mcp_tool("mcp_servers/postgres_server.py", "execute_query", {"sql": sql}))

    def list_tables(self) -> list:
        return _run(_call_mcp_tool("mcp_servers/postgres_server.py", "list_tables", {}))

    def describe_table(self, table_name: str) -> list:
        return _run(_call_mcp_tool("mcp_servers/postgres_server.py", "describe_table", {"table_name": table_name}))

    # Exchange rate server
    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> dict:
        return _run(_call_mcp_tool("mcp_servers/exchange_rate_server.py", "convert_currency", {
            "amount": amount, "from_currency": from_currency, "to_currency": to_currency
        }))

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> dict:
        return _run(_call_mcp_tool("mcp_servers/exchange_rate_server.py", "get_exchange_rate", {
            "from_currency": from_currency, "to_currency": to_currency
        }))

    # Document server
    def export_report(self, title: str, content: str, fmt: str = "pdf") -> dict:
        return _run(_call_mcp_tool("mcp_servers/document_server.py", "export_report", {
            "title": title, "content": content, "format": fmt
        }))


mcp_client = MCPClient()