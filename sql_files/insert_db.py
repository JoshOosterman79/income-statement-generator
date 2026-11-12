import sqlite3
import pandas as pd


def insert_shipments(shipments):

    conn = sqlite3.connect("database/shipments.db")
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executemany("""
    INSERT INTO shipments (
        id,
        shipment_id,
        cost_shipping,
        date_shipping,
        carrier,
        date_customs,
        cost_customs,
        total_costs,
        proxy,
        shipping_name
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

    ON CONFLICT(shipment_id)
    DO UPDATE SET
        cost_shipping = excluded.cost_shipping,
        date_shipping = excluded.date_shipping,
        carrier = excluded.carrier,
        date_customs = excluded.date_customs,
        cost_customs = excluded.cost_customs,
        total_costs = excluded.total_costs,
        proxy = excluded.proxy,
        shipping_name = excluded.shipping_name
    """, shipments)

    conn.commit()
    conn.close()

def insert_shipment_entries(entries):

    conn = sqlite3.connect("database/shipments.db")
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executemany("""
    INSERT INTO shipmententries (
        id,
        order_number,
        shipment_id,
        title,
        purchase_cost,
        quantity,
        cog_per,
        creation_date,
        purchase_date,
        proxy,
        shipping_name
    )
    VALUES (? ,?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

    ON CONFLICT(order_number)
    DO UPDATE SET
        title = excluded.title,
        purchase_cost = excluded.purchase_cost,
        quantity = excluded.quantity,
        cog_per = excluded.cog_per,
        creation_date = excluded.creation_date,
        purchase_date = excluded.purchase_date,
        proxy = excluded.proxy,
        shipping_name = excluded.shipping_name
    """, entries)

    conn.commit()
    conn.close()