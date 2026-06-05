import os
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy import create_engine
from dotenv import load_dotenv
from pathlib import Path
import tempfile

load_dotenv()

router = APIRouter()

def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}"
        f"@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DATABASE')}"
    )

@router.post("/upload/csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    # clean table name from filename
    table_name = Path(file.filename).stem.lower()
    table_name = ''.join(c if c.isalnum() else '_' for c in table_name)
    table_name = f"upload_{table_name}"

    try:
        # read CSV
        contents = await file.read()
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        df = pd.read_csv(tmp_path)
        os.unlink(tmp_path)

        # clean column names
        df.columns = [c.lower().replace(' ', '_').replace('-', '_') for c in df.columns]

        # load into PostgreSQL
        engine = get_engine()
        df.to_sql(table_name, engine, if_exists='replace', index=False)

        # rebuild RAG schema index to include new table
        from agent.schema_rag import build_schema_index
        build_schema_index()

        return {
            "success": True,
            "table_name": table_name,
            "rows": len(df),
            "columns": list(df.columns),
            "message": f"Loaded {len(df):,} rows into table '{table_name}'"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets")
async def list_datasets():
    """List all available datasets — both preloaded and uploaded."""
    from agent.mcp_client import mcp_client
    tables = mcp_client.list_tables()

    preloaded = [t for t in tables if t.startswith('olist_') or t == 'product_category_name_translation']
    uploaded = [t for t in tables if t.startswith('upload_')]
    other = [t for t in tables if t not in preloaded and t not in uploaded and t != 'chat_sessions']

    return {
        "preloaded": preloaded,
        "uploaded": uploaded,
        "other": other,
        "total": len(tables)
    }


@router.delete("/upload/{table_name}")
async def delete_dataset(table_name: str):
    """Delete an uploaded dataset."""
    if not table_name.startswith('upload_'):
        raise HTTPException(status_code=400, detail="Can only delete uploaded datasets")

    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv('PG_HOST'),
            port=os.getenv('PG_PORT'),
            database=os.getenv('PG_DATABASE'),
            user=os.getenv('PG_USER'),
            password=os.getenv('PG_PASSWORD')
        )
        cursor = conn.cursor()
        cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        conn.commit()
        cursor.close()
        conn.close()

        # rebuild RAG index
        from agent.schema_rag import build_schema_index
        build_schema_index()

        return {"success": True, "message": f"Table '{table_name}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))