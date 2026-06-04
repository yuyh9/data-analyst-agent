import json
import os
import psycopg2
import psycopg2.extras
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()


# ChromaDB persistent storage
CHROMA_PATH = "data/chroma"

# OpenAI embedding function
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)

def get_pg_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        database=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD")
    )

def build_schema_index():
    """
    Run once at startup.
    Reads all table schemas from PostgreSQL,
    embeds them into ChromaDB.
    """
    conn = get_pg_conn()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # get all tables
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = [row["table_name"] for row in cursor.fetchall()]

    # build schema text for each table
    documents = []
    metadatas = []
    ids = []

    for table in tables:
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        columns = cursor.fetchall()

        # format schema as readable text for embedding
        col_descriptions = ", ".join(
            f"{row['column_name']} ({row['data_type']})"
            for row in columns
        )
        schema_text = f"Table: {table}\nColumns: {col_descriptions}"

        documents.append(schema_text)
        metadatas.append({"table_name": table})
        ids.append(table)

    cursor.close()
    conn.close()

    # store in ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # delete existing collection if rebuilding
    try:
        client.delete_collection("table_schemas")
    except Exception:
        pass

    collection = client.create_collection(
        name="table_schemas",
        embedding_function=openai_ef
    )
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"Schema index built: {len(documents)} tables embedded")
    return collection

def get_collection():
    """Get existing ChromaDB collection."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(
        name="table_schemas",
        embedding_function=openai_ef
    )

def retrieve_relevant_schemas(query: str, top_k: int = 3) -> str:
    """
    Given a user query, retrieve the top_k most relevant
    table schemas and return them as a formatted string
    to inject into the prompt.
    """
    collection = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )

    schemas = results["documents"][0]
    table_names = [m["table_name"] for m in results["metadatas"][0]]

    formatted = "\n\n".join(schemas)
    return formatted, table_names

if __name__ == "__main__":
    # run this once to build the index
    build_schema_index()

    # test retrieval
    test_queries = [
        "which product category has the most orders",
        "total revenue by state",
        "average review score per seller",
        "most popular payment method"
    ]

    print("\n--- Retrieval test ---")
    for q in test_queries:
        _, tables = retrieve_relevant_schemas(q)
        print(f"Q: {q}")
        print(f"   Retrieved: {tables}\n")