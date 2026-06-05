import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

DATA_DIR = Path("data")

FILES = {
    "olist_customers": "olist_customers_dataset.csv",
    "olist_orders": "olist_orders_dataset.csv",
    "olist_order_items": "olist_order_items_dataset.csv",
    "olist_order_payments": "olist_order_payments_dataset.csv",
    "olist_order_reviews": "olist_order_reviews_dataset.csv",
    "olist_products": "olist_products_dataset.csv",
    "olist_sellers": "olist_sellers_dataset.csv",
    "product_category_name_translation": "product_category_name_translation.csv",
}

def get_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        database=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD")
    )

def load():
    conn = get_conn()
    for table_name, filename in FILES.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"MISSING: {filename} — skipping")
            continue
        df = pd.read_csv(filepath)

        # clean column names — lowercase, no spaces
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]

        # use pandas + sqlalchemy for easy bulk load
        from sqlalchemy import create_engine
        engine = create_engine(
            f"postgresql+psycopg2://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}"
            f"@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DATABASE')}"
        )
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        print(f"Loaded {table_name}: {len(df):,} rows")

    conn.close()
    print(f"\nDone. All tables loaded into PostgreSQL database: olist")

if __name__ == "__main__":
    load()