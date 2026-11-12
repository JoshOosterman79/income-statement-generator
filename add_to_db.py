import pandas as pd
import sqlite3
import json
from pathlib import Path 
from sql_files.create_db import create_shipments, create_shipment_entries
from sql_files.insert_db import insert_shipments, insert_shipment_entries
from sql_files.read_db import read_db_shipments, read_db_shipment_entries


current_folder = Path(__file__).parent

data_folder = "income_statement_project.xlsx"

        

def input_shipments_to_db():

    columns = [
    "id",
    "shipment_id",
    "cost_shipping",
    "date_shipping",
    "carrier",
    "date_customs",
    "cost_customs",
    "total_costs",
    "proxy",
    "shipping_name"

    ]  

    df = pd.read_excel(data_folder, sheet_name="staging_shipping_tb", index_col=None)
    df = df.iloc[2:].copy()


    df["Unnamed: 1"] = df["Unnamed: 1"].astype("string").str.strip()

    entries = list(df.itertuples(index=None, name=None))


    insert_shipments(entries)
    if insert_shipments:
        print(f"{len(df)} entries has been added to the Shipment table")
        df_read = read_db_shipments()
        df_read["shipment_id"] = df_read["shipment_id"].astype("string")

        df_read.to_csv("shipments.csv", index=None, columns=columns)


def input_shipment_entries_to_db():
    columns = [
    "id",
    "order_number",
    "shipment_id",
    "title",
    "purchase_cost",
    "quantity",
    "cog_per",
    "creation_date",
    "purchase_date",
    "proxy",
    "shipping_name",
    ]

    df = pd.read_excel(data_folder, sheet_name="staging_shipping_entries", index_col=None)

    df = df.iloc[2:].copy()

    print(df.columns)


    entries = list(df.itertuples(index=None, name=None))


    insert_shipment_entries(entries)
    if insert_shipment_entries:
        print(f"{len(df)} entries has been added to the Shipment Entries table")
        df_read = read_db_shipment_entries()
        df_read.to_csv("shipment_entries.csv", index=None, columns=columns)


input_shipments_to_db()
input_shipment_entries_to_db()



