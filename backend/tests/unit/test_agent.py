import pytest
import json
from unittest.mock import patch, MagicMock

# tool routing 
def test_only_select_allowed():
    """Postgres MCP server blocks non-SELECT statements."""
    from mcp_servers.postgres_server import call_tool
    import asyncio
    result = asyncio.run(call_tool("execute_query", {"sql": "DROP TABLE olist_orders"}))
    text = json.loads(result[0].text)
    assert "error" in text
    assert "SELECT" in text["error"]

def test_list_tables_returns_olist_tables():
    """Database has all 8 Olist tables loaded."""
    from agent.mcp_client import mcp_client
    tables = mcp_client.list_tables()
    olist_tables = [t for t in tables if t.startswith('olist_') or t == 'product_category_name_translation']
    assert len(olist_tables) == 8
    assert 'chat_sessions' in tables 

def test_describe_table_returns_columns():
    """describe_table returns column list for known table."""
    from agent.mcp_client import mcp_client
    columns = mcp_client.describe_table("olist_orders")
    names = [c["name"] for c in columns]
    assert "order_id" in names
    assert "order_status" in names

# self-check / retry 
def test_validate_result_zero_rows():
    """Self-check fails on empty result set."""
    from agent.sql_gen import validate_result
    result = validate_result([], "how many orders")
    assert result["valid"] is False
    assert "zero rows" in result["reason"]

def test_validate_result_all_null():
    """Self-check fails when all values are NULL."""
    from agent.sql_gen import validate_result
    rows = [{"order_id": None, "total": None}]
    result = validate_result(rows, "total revenue")
    assert result["valid"] is False
    assert "NULL" in result["reason"]

def test_validate_result_negative_price():
    """Self-check fails on negative price values."""
    from agent.sql_gen import validate_result
    rows = [{"payment_value": -100.0}]
    result = validate_result(rows, "total revenue")
    assert result["valid"] is False
    assert "Negative" in result["reason"]

def test_validate_result_passes_normal_data():
    """Self-check passes on normal Olist data."""
    from agent.sql_gen import validate_result
    rows = [
        {"customer_state": "SP", "order_count": 41746},
        {"customer_state": "RJ", "order_count": 12852},
    ]
    result = validate_result(rows, "orders by state")
    assert result["valid"] is True

# memory 
def test_memory_stores_messages():
    """Session memory persists messages across turns."""
    from agent.memory import MemoryStore
    store = MemoryStore()
    session = store.get_or_create("test_session")
    session.add_user_message("hello")
    session.add_assistant_message("hi there")
    msgs = session.to_openai_format()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"

def test_memory_chart_preference():
    """Session memory stores and returns chart preference."""
    from agent.memory import MemoryStore
    store = MemoryStore()
    session = store.get_or_create("test_pref")
    session.update_chart_preference("pie")
    assert session.preferred_chart_type == "pie"