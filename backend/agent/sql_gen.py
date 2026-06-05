import os
import json
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from openai import OpenAI
from agent.schema_rag import normalize_category_names

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_pg_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        database=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD")
    )

def validate_result(rows: list[dict], query: str) -> dict:
    """
    Semantic self-check — verify result makes business sense.
    Returns {"valid": True} or {"valid": False, "reason": "..."}
    """
    if len(rows) == 0:
        return {"valid": False, "reason": "Query returned zero rows — possible wrong JOIN or bad filter"}

    # check for all-NULL results
    first_row = rows[0]
    all_null = all(v is None for v in first_row.values())
    if all_null:
        return {"valid": False, "reason": "All values are NULL — check JOIN conditions"}

    # check numeric ranges for known Olist fields
    for row in rows[:10]:
        for col, val in row.items():
            if val is None:
                continue
            col_lower = col.lower()

            # price / payment values should be positive and reasonable
            if any(k in col_lower for k in ["price", "payment", "value", "total", "freight"]):
                try:
                    num = float(val)
                    if num < 0:
                        return {"valid": False, "reason": f"Negative value in {col}: {num}"}
                    # raised threshold to 100M to allow total revenue queries
                    if num > 100_000_000:
                        return {"valid": False, "reason": f"Suspiciously large value in {col}: {num} — possible duplicate JOIN"}
                except (TypeError, ValueError):
                    pass

            # review scores should be 0-5
            if "review_score" in col_lower or "score" in col_lower:
                try:
                    num = float(val)
                    if not (0 <= num <= 5):
                        return {"valid": False, "reason": f"Review score out of range: {num}"}
                except (TypeError, ValueError):
                    pass

            # dates should be within Olist range 2016-2018
            if "date" in col_lower or "timestamp" in col_lower:
                try:
                    date_str = str(val)[:4]
                    year = int(date_str)
                    if year < 2016 or year > 2019:
                        return {"valid": False, "reason": f"Date out of expected range (2016-2018): {val}"}
                except (TypeError, ValueError):
                    pass

    return {"valid": True}

def generate_and_validate_sql(
    query: str,
    schema_context: str,
    conversation_history: list[dict],
    max_retries: int = 3
) -> dict:
    """
    Generate SQL from natural language, execute it,
    run self-check, retry on failure.
    Returns final result rows or error.
    """
    system_prompt = f"""You are a PostgreSQL expert. Generate SQL queries for the Olist Brazilian e-commerce database.

Available table schemas:
{schema_context}

Rules:
- Only write SELECT statements
- Use exact table and column names from the schemas above
- For category names always use the English underscore format from product_category_name_translation e.g. health_beauty, watches_gifts, bed_bath_table
- For date/year filters always JOIN with olist_orders and use order_purchase_timestamp
- Olist data covers September 2016 to October 2018
- Always use LIMIT 50 unless the user asks for all data
- Return only the SQL query, nothing else
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages += conversation_history
    messages.append({"role": "user", "content": f"Write a SQL query for: {query}"})

    last_error = None
    attempts = []

    for attempt in range(1, max_retries + 1):
        # if previous attempt failed, add error context
        if last_error:
            messages.append({
                "role": "user",
                "content": f"That SQL failed with error: {last_error}\nPlease fix the SQL and try again."
            })

        # generate SQL with 60s timeout
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            timeout=60
        )
        sql = response.choices[0].message.content.strip()

        # clean up markdown code blocks if model adds them
        if sql.startswith("```"):
            sql = sql.split("```")[1]
            if sql.startswith("sql"):
                sql = sql[3:]
            sql = sql.strip()

        # normalize category display names to database format
        # e.g. 'Health & Beauty' → 'health_beauty'
        sql = normalize_category_names(sql)

        # try to execute
        try:
            conn = get_pg_conn()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            rows = cursor.fetchmany(500)
            rows = [dict(row) for row in rows]
            cursor.close()
            conn.close()

            # run semantic self-check
            check = validate_result(rows, query)
            attempts.append({
                "attempt": attempt,
                "sql": sql,
                "rows": len(rows),
                "check": check
            })

            if check["valid"]:
                return {
                    "success": True,
                    "sql": sql,
                    "rows": rows,
                    "attempts": attempts
                }
            else:
                last_error = f"Semantic check failed: {check['reason']}"
                messages.append({
                    "role": "assistant",
                    "content": sql
                })

        except Exception as e:
            last_error = str(e)
            attempts.append({
                "attempt": attempt,
                "sql": sql,
                "error": last_error
            })
            messages.append({
                "role": "assistant",
                "content": sql
            })

    # all retries exhausted
    return {
        "success": False,
        "error": f"Failed after {max_retries} attempts. Last error: {last_error}",
        "attempts": attempts
    }