import json
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("exchange-rate-server")

BASE_URL = "https://api.exchangerate-api.com/v4/latest"

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="convert_currency",
            description="Convert an amount from one currency to another using live exchange rates. Use this when the user asks for amounts in a specific currency.",
            inputSchema={
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "The amount to convert"
                    },
                    "from_currency": {
                        "type": "string",
                        "description": "Source currency code e.g. BRL, USD, EUR"
                    },
                    "to_currency": {
                        "type": "string",
                        "description": "Target currency code e.g. USD, EUR, JPY"
                    }
                },
                "required": ["amount", "from_currency", "to_currency"]
            }
        ),
        Tool(
            name="get_exchange_rate",
            description="Get the current exchange rate between two currencies without converting a specific amount.",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_currency": {
                        "type": "string",
                        "description": "Source currency code e.g. BRL"
                    },
                    "to_currency": {
                        "type": "string",
                        "description": "Target currency code e.g. USD"
                    }
                },
                "required": ["from_currency", "to_currency"]
            }
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:

            if name == "get_exchange_rate":
                from_currency = arguments["from_currency"].upper()
                to_currency = arguments["to_currency"].upper()
                response = await client.get(f"{BASE_URL}/{from_currency}")
                response.raise_for_status()
                data = response.json()
                rate = data["rates"].get(to_currency)
                if rate is None:
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": f"Currency {to_currency} not found"})
                    )]
                return [TextContent(type="text", text=json.dumps({
                    "from": from_currency,
                    "to": to_currency,
                    "rate": rate,
                    "date": data.get("date")
                }))]

            elif name == "convert_currency":
                amount = arguments["amount"]
                from_currency = arguments["from_currency"].upper()
                to_currency = arguments["to_currency"].upper()
                response = await client.get(f"{BASE_URL}/{from_currency}")
                response.raise_for_status()
                data = response.json()
                rate = data["rates"].get(to_currency)
                if rate is None:
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": f"Currency {to_currency} not found"})
                    )]
                converted = round(amount * rate, 2)
                return [TextContent(type="text", text=json.dumps({
                    "original_amount": amount,
                    "from": from_currency,
                    "to": to_currency,
                    "rate": rate,
                    "converted_amount": converted,
                    "date": data.get("date")
                }))]

            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown tool: {name}"})
                )]

    except httpx.HTTPError as e:
        return [TextContent(type="text", text=json.dumps({"error": f"HTTP error: {str(e)}"}))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())