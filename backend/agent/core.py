import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from agent.schema_rag import retrieve_relevant_schemas, build_schema_index
from agent.sql_gen import generate_and_validate_sql
from agent.chart_gen import generate_chart
from agent.memory import memory_store
from agent.mcp_client import mcp_client

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": "Query the database using natural language. Use for any question about the data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The data question to answer with SQL"}
                },
                "required": ["question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": "Convert an amount from one currency to another using live exchange rates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Amount to convert"},
                    "from_currency": {"type": "string", "description": "Source currency code e.g. BRL, USD, EUR"},
                    "to_currency": {"type": "string", "description": "Target currency code e.g. USD, EUR, JPY"}
                },
                "required": ["amount", "from_currency", "to_currency"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_chart",
            "description": "Generate a chart from data rows. Call after query_database to visualize results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rows": {"type": "array", "description": "Array of data rows", "items": {"type": "object"}},
                    "query": {"type": "string", "description": "The original user question"},
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "pie", "scatter", "histogram"],
                        "description": "Chart type"
                    }
                },
                "required": ["rows", "query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_report",
            "description": "Export the analysis as a Word or PDF report. Use when user asks to export, save, download, or generate a report.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Report title"},
                    "content": {"type": "string", "description": "Full report content"},
                    "format": {"type": "string", "enum": ["docx", "pdf"], "description": "Output format"}
                },
                "required": ["title", "content", "format"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are a data analyst assistant. You help users explore and understand their data through SQL queries, charts, and reports.

Your capabilities:
- Query any database table using natural language
- Convert currencies using live exchange rates
- Generate charts to visualize data
- Export analysis as Word (.docx) or PDF reports

Guidelines:
- Always query the database first before generating a chart
- For currency questions, query first then convert the total
- Be concise and specific — include key numbers in your response
- If the user asks to export, save, or download a report, use export_report
- When exporting, include the full analysis content in the report
"""


def handle_tool_call(tool_name: str, tool_args: dict, session_id: str) -> str:
    session = memory_store.get_or_create(session_id)

    if tool_name == "query_database":
        question = tool_args["question"]
        schema_context, tables_used = retrieve_relevant_schemas(question)
        session.last_tables_used = tables_used
        result = generate_and_validate_sql(
            query=question,
            schema_context=schema_context,
            conversation_history=session.to_openai_format()
        )
        if result["success"]:
            return json.dumps({
                "rows": result["rows"][:50],
                "sql": result["sql"],
                "row_count": len(result["rows"]),
                "attempts": len(result["attempts"])
            }, default=str)
        return json.dumps({"error": result["error"]})

    elif tool_name == "convert_currency":
        result = mcp_client.convert_currency(
            tool_args["amount"],
            tool_args["from_currency"],
            tool_args["to_currency"]
        )
        return json.dumps(result)

    elif tool_name == "generate_chart":
        rows = tool_args["rows"]
        query = tool_args["query"]
        chart_type = tool_args.get("chart_type")
        if chart_type:
            session.update_chart_preference(chart_type)
        elif session.preferred_chart_type:
            chart_type = session.preferred_chart_type
        result = generate_chart(rows, query, chart_type)
        return json.dumps(result)

    elif tool_name == "export_report":
        result = mcp_client.export_report(
            title=tool_args["title"],
            content=tool_args["content"],
            fmt=tool_args.get("format", "pdf")
        )
        return json.dumps(result)

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def chat(user_message: str, session_id: str = "default") -> dict:
    session = memory_store.get_or_create(session_id)
    session.add_user_message(user_message)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += session.to_openai_format()

    chart_filepath = None
    report_filepath = None
    final_text = ""

    for _ in range(10):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            seed=42,
            temperature=0
        )
        message = response.choices[0].message

        if not message.tool_calls:
            final_text = message.content or ""
            break

        messages.append(message)

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            result = handle_tool_call(tool_name, tool_args, session_id)

            try:
                result_data = json.loads(result)
                if "filepath" in result_data:
                    if tool_name == "generate_chart":
                        chart_filepath = result_data["filepath"]
                    elif tool_name == "export_report":
                        report_filepath = result_data["filepath"]
            except Exception:
                pass

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    session.add_assistant_message(final_text)
    memory_store.save(session_id)

    return {
        "answer": final_text,
        "chart_filepath": chart_filepath,
        "report_filepath": report_filepath,
        "session_id": session_id,
        "tables_used": session.last_tables_used
    }


def initialize():
    print("Building schema index...")
    build_schema_index()
    print("Agent ready.")