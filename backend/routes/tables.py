from fastapi import APIRouter

from agent.mcp_client import mcp_client

router = APIRouter()


# endpoints
@router.get("/tables")
def list_tables():
    tables = mcp_client.list_tables()
    return {"tables": tables}


@router.get("/tables/{table_name}")
def describe_table(table_name: str):
    columns = mcp_client.describe_table(table_name)
    return {"table": table_name, "columns": columns}