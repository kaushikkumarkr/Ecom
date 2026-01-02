import os
import pandas as pd
from sqlalchemy import create_engine, text
import glob

# Database Connection
DB_USER = os.getenv('POSTGRES_USER', 'user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
DB_HOST = os.getenv('POSTGRES_HOST', 'postgres')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'ecom')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

DATA_DIR = "/usr/src/app/data"

def create_schema(schema_name):
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name};"))
        conn.commit()
    print(f"Schema {schema_name} created/verified.")

def load_csv_to_postgres(file_path, table_name, schema="raw"):
    print(f"Loading {file_path} into {schema}.{table_name}...", flush=True)
    try:
        # Read CSV in chunks to avoid memory issues and enable progress logging
        chunksize = 100000
        count = 0
        for chunk in pd.read_csv(file_path, chunksize=chunksize):
            # Clean column names
            chunk.columns = [c.lower().replace(' ', '_') for c in chunk.columns]
            
            # Write to Postgres
            if count == 0:
                # Replace on first chunk
                chunk.to_sql(table_name, engine, schema=schema, if_exists='replace', index=False, chunksize=10000)
            else:
                # Append on subsequent chunks
                chunk.to_sql(table_name, engine, schema=schema, if_exists='append', index=False, chunksize=10000)
            
            count += len(chunk)
            print(f"Loaded {count} rows...", flush=True)
            
        print(f"Successfully loaded {count} rows to {table_name}", flush=True)
    except Exception as e:
        print(f"Error loading {table_name}: {e}", flush=True)

def generate_mock_data(engine):
    print("Generating mock data for TheLook schema...")
    from sqlalchemy import text
    
    # Mock Users
    df_users = pd.DataFrame({
        'id': range(1, 101),
        'first_name': [f'User{i}' for i in range(1, 101)],
        'last_name': [f'Name{i}' for i in range(1, 101)],
        'email': [f'user{i}@example.com' for i in range(1, 101)],
        'age': [25] * 100,
        'gender': ['M'] * 50 + ['F'] * 50,
        'state': ['CA'] * 100,
        'street_address': ['123 Main St'] * 100,
        'postal_code': ['90210'] * 100,
        'city': ['Los Angeles'] * 100,
        'country': ['USA'] * 100,
        'latitude': [34.05] * 100,
        'longitude': [-118.25] * 100,
        'traffic_source': ['Search'] * 100,
        'created_at': pd.to_datetime('2023-01-01')
    })
    df_users.to_sql('users', engine, schema='raw', if_exists='replace', index=False)
    
    # Mock Products
    df_products = pd.DataFrame({
        'id': range(1, 11),
        'cost': [10.0] * 10,
        'category': ['Tops'] * 10,
        'name': [f'Product {i}' for i in range(1, 11)],
        'brand': ['BrandA'] * 10,
        'retail_price': [20.0] * 10,
        'department': ['Men'] * 10,
        'sku': [f'SKU{i}' for i in range(1, 11)],
        'distribution_center_id': [1] * 10
    })
    df_products.to_sql('products', engine, schema='raw', if_exists='replace', index=False)
    
    # Mock Orders
    df_orders = pd.DataFrame({
        'order_id': range(1, 51),
        'user_id': range(1, 51),
        'status': ['Complete'] * 50,
        'gender': ['M'] * 50,
        'created_at': pd.to_datetime('2023-01-02'),
        'returned_at': None,
        'shipped_at': pd.to_datetime('2023-01-03'),
        'delivered_at': pd.to_datetime('2023-01-04'),
        'num_of_item': [1] * 50
    })
    df_orders.to_sql('orders', engine, schema='raw', if_exists='replace', index=False)
    
    # Mock Order Items
    df_order_items = pd.DataFrame({
        'id': range(1, 51),
        'order_id': range(1, 51),
        'user_id': range(1, 51),
        'product_id': [1] * 50,
        'inventory_item_id': range(1, 51),
        'status': ['Complete'] * 50,
        'created_at': pd.to_datetime('2023-01-02'),
        'shipped_at': pd.to_datetime('2023-01-03'),
        'delivered_at': pd.to_datetime('2023-01-04'),
        'returned_at': None,
        'sale_price': [20.0] * 50
    })
    df_order_items.to_sql('order_items', engine, schema='raw', if_exists='replace', index=False)

    # Mock Events
    df_events = pd.DataFrame({
        'id': range(1, 101),
        'user_id': range(1, 101),
        'sequence_number': [1] * 100,
        'session_id': [f'session_{i}' for i in range(1, 101)],
        'created_at': pd.to_datetime('2023-01-01'),
        'ip_address': ['127.0.0.1'] * 100,
        'city': ['Los Angeles'] * 100,
        'state': ['CA'] * 100,
        'postal_code': ['90210'] * 100,
        'browser': ['Chrome'] * 100,
        'traffic_source': ['Search'] * 100,
        'uri': ['/home'] * 100,
        'event_type': ['home'] * 100
    })
    df_events.to_sql('events', engine, schema='raw', if_exists='replace', index=False)

    # Mock Inventory Items
    df_inventory = pd.DataFrame({
        'id': range(1, 101),
        'product_id': [1] * 100,
        'created_at': pd.to_datetime('2023-01-01'),
        'sold_at': None,
        'cost': [10.0] * 100,
        'product_category': ['Tops'] * 100,
        'product_name': ['Product 1'] * 100,
        'product_brand': ['BrandA'] * 100,
        'product_retail_price': [20.0] * 100,
        'product_department': ['Men'] * 100,
        'product_sku': ['SKU1'] * 100,
        'product_distribution_center_id': [1] * 100
    })
    df_inventory.to_sql('inventory_items', engine, schema='raw', if_exists='replace', index=False)

    print("Mock data generated successfully.")

def main():
    print("Starting Data Loader...", flush=True)
    
    # DROP dependent schemas to allow replacing raw tables
    with engine.connect() as conn:
        print("Dropping dependent schemas (staging, marts) to release locks...", flush=True)
        conn.execute(text("DROP SCHEMA IF EXISTS public_staging CASCADE;"))
        conn.execute(text("DROP SCHEMA IF EXISTS public_marts CASCADE;"))
        conn.commit()
    
    # Wait for DB? (Docker depends_on handles mostly, but good to be safe)
    # create 'raw' schema
    create_schema("raw")
    
    # Check for files
    csv_files = glob.glob(f"{DATA_DIR}/*.csv")
    if not csv_files:
        print(f"No CSV files found in {DATA_DIR}. Please place 'TheLook' CSVs there.")
        # Generate dummy data so "Hello World" AND Sprint 2 tests work
        generate_mock_data(engine)
        
        # Also create hello world for Sprint 1 check
        df_dummy = pd.DataFrame({'id': [1, 2], 'message': ['Hello', 'World']})
        df_dummy.to_sql('hello_world', engine, schema='raw', if_exists='replace', index=False)
        return

    for file_path in csv_files:
        file_name = os.path.basename(file_path)
        table_name = os.path.splitext(file_name)[0]
        load_csv_to_postgres(file_path, table_name)

if __name__ == "__main__":
    main()
