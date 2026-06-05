import json
import os
import psycopg2
import psycopg2.extras
import chromadb
import re
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

# category name mapping — display name to database underscore format
# used by normalize_category_names() to fix SQL before execution
CATEGORY_MAP = {
    "health & beauty": "health_beauty",
    "watches & gifts": "watches_gifts",
    "bed, bath & table": "bed_bath_table",
    "sports & leisure": "sports_leisure",
    "computers & accessories": "computers_accessories",
    "furniture & decor": "furniture_decor",
    "housewares": "housewares",
    "auto": "auto",
    "garden tools": "garden_tools",
    "toys": "toys",
    "telephony": "telephony",
    "fashion bags & accessories": "fashion_bags_accessories",
    "office furniture": "office_furniture",
    "electronics": "electronics",
    "perfumery": "perfumery",
    "books general interest": "books_general_interest",
    "cool stuff": "cool_stuff",
    "musical instruments": "musical_instruments",
    "food & drink": "food_drink",
    "art": "art",
    "baby": "baby",
    "christmas supplies": "christmas_supplies",
    "cds dvds musicals": "cds_dvds_musicals",
    "fashion childrens clothes": "fashion_childrens_clothes",
    "flowers": "flowers",
    "food": "food",
    "home comfort": "home_comfort",
    "home construction": "home_construction",
    "industry commerce and business": "industry_commerce_and_business",
    "luggage accessories": "luggage_accessories",
    "small appliances": "small_appliances",
    "stationery": "stationery",
    "tablets printing image": "tablets_printing_image",
}

# force-include rules — always add these tables when keywords detected
FORCE_INCLUDE_RULES = {
    # review queries need bridge table to JOIN reviews → categories
    "review":   ["olist_order_reviews", "olist_order_items"],
    "rating":   ["olist_order_reviews", "olist_order_items"],
    "score":    ["olist_order_reviews", "olist_order_items"],
    # time-based queries need olist_orders for order_purchase_timestamp
    "2016":     ["olist_orders"],
    "2017":     ["olist_orders"],
    "2018":     ["olist_orders"],
    "year":     ["olist_orders"],
    "month":    ["olist_orders"],
    "monthly":  ["olist_orders"],
    "date":     ["olist_orders"],
    "annual":   ["olist_orders"],
}


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
    Reads all table schemas from PostgreSQL and embeds them into ChromaDB.
    Enriches the translation table with actual category mappings
    so the agent knows display name → database name.
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

        col_descriptions = ", ".join(
            f"{row['column_name']} ({row['data_type']})"
            for row in columns
        )

        # enrich translation table with actual category mappings
        # so RAG retrieves it for category-related queries
        if table == "product_category_name_translation":
            try:
                cursor.execute("""
                    SELECT product_category_name, product_category_name_english
                    FROM product_category_name_translation
                    ORDER BY product_category_name_english
                """)
                mappings = cursor.fetchall()
                mapping_text = "\n".join([
                    f"  {r['product_category_name']} → {r['product_category_name_english']}"
                    for r in mappings
                ])
                schema_text = (
                    f"Table: {table}\n"
                    f"Columns: {col_descriptions}\n"
                    f"Category mappings (Portuguese → English database name):\n"
                    f"{mapping_text}\n"
                    f"Use product_category_name_english values in WHERE clauses."
                )
            except Exception:
                schema_text = f"Table: {table}\nColumns: {col_descriptions}"
        else:
            schema_text = f"Table: {table}\nColumns: {col_descriptions}"

        documents.append(schema_text)
        metadatas.append({"table_name": table})
        ids.append(table)

    cursor.close()
    conn.close()

    # store in ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_PATH)

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


def normalize_category_names(sql: str) -> str:
    """
    Post-process SQL to replace display category names with database format.
    Handles cases where agent uses 'Health & Beauty' instead of 'health_beauty'.
    Applied automatically before SQL execution.
    """
    for display_name, db_name in CATEGORY_MAP.items():
        # replace inside SQL string literals — case insensitive
        pattern = re.escape(display_name)
        sql = re.sub(pattern, db_name, sql, flags=re.IGNORECASE)
    return sql


def retrieve_relevant_schemas(query: str, top_k: int = 4) -> tuple:
    """
    Retrieve the most relevant table schemas for a given query.
    Also applies force-include rules for bridge tables.

    Args:
        query: natural language question from the user
        top_k: number of tables to retrieve (default 4)

    Returns:
        tuple of (schema_text, table_names)
    """
    collection = get_collection()

    # vector search — find top_k most similar table schemas
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )

    schemas = results["documents"][0]
    table_names = [m["table_name"] for m in results["metadatas"][0]]

    # apply force-include rules — add bridge tables based on keywords
    query_lower = query.lower()
    for keyword, required_tables in FORCE_INCLUDE_RULES.items():
        if keyword in query_lower:
            for required_table in required_tables:
                if required_table not in table_names:
                    try:
                        forced = collection.get(
                            ids=[required_table],
                            include=["documents", "metadatas"]
                        )
                        if forced["documents"]:
                            schemas.append(forced["documents"][0])
                            table_names.append(required_table)
                    except Exception:
                        pass

    formatted = "\n\n".join(schemas)
    return formatted, table_names

if __name__ == "__main__":
    # rebuild index with enriched schemas
    build_schema_index()

    # test retrieval
    test_queries = [
        "which product category has the most orders",
        "total revenue by state",
        "average review score per seller",
        "most popular payment method",
        "which of health beauty watches gifts has best reviews"
    ]

    print("\n--- Retrieval test ---")
    for q in test_queries:
        _, tables = retrieve_relevant_schemas(q)
        print(f"Q: {q}")
        print(f"   Retrieved: {tables}\n")