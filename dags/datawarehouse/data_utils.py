from airflow.providers.postgres.hooks.postgres import PostgresHook
from psycopg2 import RealDictCursor


table = "products"


def get_conn_cursor():
    """Get a connection and cursor to the Postgres database using Airflow's PostgresHook."""
    hook = PostgresHook(postgres_conn_id="postgres_default", database="products_elt")
    conn = hook.get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
 

def close_conn_cursor(conn, cursor):
    """Close the cursor and connection to the Postgres database."""     
    cursor.close()
    conn.close()

def create_schema(schema) -> None:
    """Create a schema in the Postgres database if it doesn't already exist."""
    conn, cursor = get_conn_cursor()
    
    schema_sql = f"CREATE SCHEMA IF NOT EXISTS {schema};"
    
    cursor.execute(schema_sql)

    conn.commit()

    close_conn_cursor(conn, cursor)

def create_table(schema, table) -> None:
    """Create a table in the Postgres database if it doesn't already exist."""
    conn, cursor = get_conn_cursor()

    if schema == 'staging':
        table_sql = f"""
        CREATE TABLE IF NOT EXISTS {schema}.{table} (
            record_id SERIAL PRIMARY KEY,
            sku VARCHAR(50) NOT NULL,
            product_name VARCHAR(255) NOT NULL,
            category VARCHAR(100),
            listed_price VARCHAR(20),
            stock_qty VARCHAR(20)
        );
        """ 
    
    else:
        table_sql = f"""
        CREATE TABLE IF NOT EXISTS {schema}.{table} (
            record_id SERIAL PRIMARY KEY,
            sku VARCHAR(50) NOT NULL,
            product_name VARCHAR(255) NOT NULL,
            category VARCHAR(100),
            listed_price NUMERIC(10, 2),
            stock_qty INT
        );
        """
    
    cursor.execute(table_sql)

    conn.commit()

    close_conn_cursor(conn, cursor)

def get_id_by_sku(schema, table, sku) -> int | None:
    """Get the record_id of a product by its SKU from the specified schema and table."""
    conn, cursor = get_conn_cursor()

    query = f"SELECT record_id FROM {schema}.{table} WHERE sku = %s;"
    cursor.execute(query, (sku,))
    result = cursor.fetchone()

    close_conn_cursor(conn, cursor)

    return result["record_id"] if result else None

