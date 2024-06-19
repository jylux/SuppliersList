import mysql.connector
from mysql.connector import Error
from BiddersListScript import config, live_suppliers
from collections import Counter

import sys
import os

# Add the directory containing BiddersListScript.py to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

def reset_and_update_tblSupplierRecon():
    try:
        # Establish the database connection using the config from BiddersListScript
        connection = mysql.connector.connect(
            host=config['host'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )

        if connection.is_connected():
            cursor = connection.cursor()
            
            # Define the SQL DELETE query to remove all entries
            delete_query = "DELETE FROM tblSupplierRecon"

            # Execute the DELETE query
            cursor.execute(delete_query)

            # Define the SQL INSERT query to add new entries
            insert_query = """
            INSERT INTO tblSupplierRecon (SN, SUP_ID, Company_Name, PROD_CODE, Bidder_Number)
            VALUES (%s, %s, %s, %s, %s)
            """
            # print (live_suppliers)
            # Execute the INSERT query for each entry
            
            # Filter to get unique suppliers based on SUP_ID
            unique_suppliers = {}
            for supplier in live_suppliers:
                sup_id = supplier[1]
                if sup_id not in unique_suppliers:
                    unique_suppliers[sup_id] = supplier

            # Convert the dictionary values back to a list
            filtered_live_suppliers = list(unique_suppliers.values())

            # Count the occurrences of each product code
            product_code_counts = Counter(supplier[3] for supplier in filtered_live_suppliers)
            print(product_code_counts)
          # Create live_bidders list
            live_bidders = [(sn, sup_id, company_name, '9.99.99' if len(product_code_counts) > 1 else prod_code, 0) for sn, sup_id, company_name, prod_code, _, _ in filtered_live_suppliers]
    
            for bidder in live_bidders:
                cursor.execute(insert_query, bidder)

            # Commit the transaction
            connection.commit()

            # Update Bidder_Number in tblSupplierRecon from tblsupplier
            update_query = """
            UPDATE tblSupplierRecon, tblsupplier
            SET tblSupplierRecon.Bidder_Number = tblsupplier.Bidder_Number
            WHERE tblSupplierRecon.SUP_ID = tblsupplier.SUP_ID;
            """
            cursor.execute(update_query)
            connection.commit()

            print("All entries deleted and new data inserted successfully, and Bidder_Number updated.")

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

# Example usage
reset_and_update_tblSupplierRecon()
