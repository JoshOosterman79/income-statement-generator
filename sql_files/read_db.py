import sqlite3
import pandas as pd



def read_db_shipments():
    conn = sqlite3.connect("database/shipments.db")

    query = f"""
        SELECT *
        FROM shipments
    """

    df = pd.read_sql(query, conn)

    conn.close()

    return df

def read_db_shipment_entries():
    conn = sqlite3.connect("database/shipments.db")
    query = f"""
        SELECT *
        FROM shipmententries
    """

    df = pd.read_sql(query, conn)

    conn.close()

    return df

