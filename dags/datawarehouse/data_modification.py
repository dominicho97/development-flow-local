
import logging

logger = logging.getLogger(__name__)
table = "products"

def insert_rows(cur,conn,schema,row):

    try:

        if schema == 'staging':

            insert_sql = f"""
            INSERT INTO {schema}.{table} (sku, product_name, category, listed_price, stock_qty)
            VALUES (%s, %s, %s, %s, %s);
            """
            cur.execute(insert_sql, (row["sku"], row["product_name"], row["category"], row["listed_price"], row["stock_qty"]))
            conn.commit()

            logger.info(f"Inserted row with SKU: {row['sku']} into {schema}.{table}.")
        else:
            # Check if the row already exists in the target table
            check_sql = f"""
            SELECT record_id FROM {schema}.{table} WHERE sku = %s;
            """
            cur.execute(check_sql, (row["sku"],))
            existing_row = cur.fetchone()

            if existing_row is None:
                insert_sql = f"""
                INSERT INTO {schema}.{table} (sku, product_name, category, listed_price, stock_qty)
                VALUES (%s, %s, %s, %s, %s);
                """
                cur.execute(insert_sql, (row["sku"], row["product_name"], row["category"], row["listed_price"], row["stock_qty"]))
                conn.commit()

                logger.info(f"Inserted row with SKU: {row['sku']} into {schema}.{table}.")
            else:
                logger.warning(f"Row with SKU: {row['sku']} already exists in {schema}.{table}. Skipping insertion.")
    except Exception as e:
        logger.error(f"Error inserting row with SKU: {row['sku']} into {schema}.{table}: {e}")
    conn.commit()

    logger.info(f"Finished processing row with SKU: {row['sku']} for {schema}.{table}.")


        
    

def update_rows(cur,conn,schema,row):

    try:
        #staging
        if schema == 'staging':
            update_sql = f"""
            UPDATE {schema}.{table}
            SET product_name = %s, category = %s, listed_price = %s, stock_qty = %s
            WHERE sku = %s;
            """
            cur.execute(update_sql, (row["product_name"], row["category"], row["listed_price"], row["stock_qty"], row["sku"]))
            conn.commit()

            logger.info(f"Updated row with SKU: {row['sku']} in {schema}.{table}.")
        else:
            # Check if the row exists in the target table
            check_sql = f"""
            SELECT record_id FROM {schema}.{table} WHERE sku = %s;
            """
            cur.execute(check_sql, (row["sku"],))
            existing_row = cur.fetchone()

            if existing_row is not None:
                update_sql = f"""
                UPDATE {schema}.{table}
                SET product_name = %s, category = %s, listed_price = %s, stock_qty = %s
                WHERE sku = %s;
                """
                cur.execute(update_sql, (row["product_name"], row["category"], row["listed_price"], row["stock_qty"], row["sku"]))
                conn.commit()

                logger.info(f"Updated row with SKU: {row['sku']} in {schema}.{table}.")
            else:
                logger.warning(f"Row with SKU: {row['sku']} does not exist in {schema}.{table}. Skipping update.")


            cur.execute(update_sql, (row["product_name"], row["category"], row["listed_price"], row["stock_qty"], row["sku"]))
            conn.commit()

            logger.info(f"Updated row with SKU: {row['sku']} in {schema}.{table}.")
    except Exception as e:
        logger.error(f"Error updating row with SKU: {row['sku']} in {schema}.{table}: {e}")

def delete_rows(cur,conn,schema,row):

    try:
        #staging
        if schema == 'staging':
            delete_sql = f"""
            DELETE FROM {schema}.{table} WHERE sku = %s;
            """
            cur.execute(delete_sql, (row["sku"],))
            conn.commit()

            logger.info(f"Deleted row with SKU: {row['sku']} from {schema}.{table}.")
        else:
            # Check if the row exists in the target table
            check_sql = f"""
            SELECT record_id FROM {schema}.{table} WHERE sku = %s;
            """
            cur.execute(check_sql, (row["sku"],))
            existing_row = cur.fetchone()

            if existing_row is not None:
                delete_sql = f"""
                DELETE FROM {schema}.{table} WHERE sku = %s;
                """
                cur.execute(delete_sql, (row["sku"],))
                conn.commit()

                logger.info(f"Deleted row with SKU: {row['sku']} from {schema}.{table}.")
            else:
                logger.warning(f"Row with SKU: {row['sku']} does not exist in {schema}.{table}. Skipping deletion.")
    except Exception as e:
        logger.error(f"Error deleting row with SKU: {row['sku']} from {schema}.{table}: {e}")