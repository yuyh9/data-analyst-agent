import json
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

OUTPUT_DIR = Path("data/charts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def detect_chart_type(query: str, rows: list[dict]) -> str:
    """
    Auto-detect the best chart type based on
    the query and the shape of the data.
    """
    query_lower = query.lower()

    # explicit user preference
    if "pie" in query_lower:
        return "pie"
    if "line" in query_lower or "trend" in query_lower or "over time" in query_lower:
        return "line"
    if "scatter" in query_lower:
        return "scatter"
    if "bar" in query_lower or "top" in query_lower or "most" in query_lower:
        return "bar"
    if "histogram" in query_lower or "distribution" in query_lower:
        return "histogram"

    # fallback based on data shape
    if len(rows) == 0:
        return "bar"
    keys = list(rows[0].keys())
    if len(keys) == 2:
        return "bar"  # label + value = bar chart
    return "bar"

def generate_chart(
    rows: list[dict],
    query: str,
    chart_type: str = None,
    title: str = None
) -> dict:
    """
    Generate a Plotly chart from query results.
    Returns a dict with chart_type, filepath, and json.
    """
    if not rows:
        return {"error": "No data to chart"}

    keys = list(rows[0].keys())
    if len(keys) < 2:
        return {"error": "Need at least 2 columns to generate a chart"}

    # auto-detect if not specified
    if chart_type is None:
        chart_type = detect_chart_type(query, rows)

    label_col = keys[0]
    value_col = keys[1]

    labels = [str(row[label_col]) for row in rows]
    values = [row[value_col] for row in rows]

    chart_title = title or query[:60]

    try:
        if chart_type == "bar":
            fig = px.bar(
                x=labels, y=values,
                title=chart_title,
                labels={"x": label_col, "y": value_col}
            )

        elif chart_type == "pie":
            fig = px.pie(
                names=labels, values=values,
                title=chart_title
            )

        elif chart_type == "line":
            fig = px.line(
                x=labels, y=values,
                title=chart_title,
                labels={"x": label_col, "y": value_col}
            )

        elif chart_type == "scatter":
            fig = px.scatter(
                x=labels, y=values,
                title=chart_title,
                labels={"x": label_col, "y": value_col}
            )

        elif chart_type == "histogram":
            fig = px.histogram(
                x=values,
                title=chart_title,
                labels={"x": value_col}
            )

        else:
            fig = px.bar(
                x=labels, y=values,
                title=chart_title
            )

        # save as PNG for demo + JSON for frontend
        filename = f"chart_{abs(hash(query))}.png"
        filepath = OUTPUT_DIR / filename
        fig.write_image(str(filepath))

        return {
            "chart_type": chart_type,
            "filepath": str(filepath),
            "plotly_json": fig.to_json(),
            "title": chart_title,
            "rows_plotted": len(rows)
        }

    except Exception as e:
        return {"error": f"Chart generation failed: {str(e)}"}