import sqlite3
import pandas as pd

def create_shipments():
    conn = sqlite3.connect("database/shipments.db")

    cursor = conn.cursor()

    cursor.execute("""
    DROP TABLE IF EXISTS shipments
    """)

    cursor.execute("""
    CREATE TABLE shipments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shipment_id TEXT UNIQUE,
        cost_shipping REAL,
        date_shipping DATE,
        carrier TEXT,
        date_customs DATE,
        cost_customs REAL,
        total_costs REAL,
        proxy TEXT,
        shipping_name TEXT
    )
    """)

    conn.commit()
    conn.close()

    print("Database created")

create_shipments()


def create_shipment_entries():
    
    conn = sqlite3.connect("database/shipments.db")
    conn.execute("PRAGMA foreign_keys = ON")

    cursor = conn.cursor()

    cursor.execute("""
    DROP TABLE IF EXISTS shipmententries
    """)

    cursor.execute("""
    CREATE TABLE shipmententries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE,
        shipment_id TEXT,
        title TEXT,
        purchase_cost REAL,
        quantity INTEGER,
        cog_per REAL,
        creation_date DATE,
        purchase_date DATE,
        proxy TEXT,
        shipping_name TEXT,
        FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
    )
    """)

    conn.commit()
    conn.close()

    print("Database created")

create_shipment_entries()

