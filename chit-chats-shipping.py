import os
import csv
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests
from datetime import datetime, timedelta, timezone


class ChitChatsClient:
    def __init__(self, client_id: str, access_token: str):
        self.base_url = f"https://chitchats.com/api/v1/clients/{client_id}"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def list_shipments(
        self,
        page: int = 1,
        limit: int = 100,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params = {
            "page": page,
            "limit": limit,
        }

        if status:
            params["status"] = status
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date

        response = self.session.get(f"{self.base_url}/shipments", params=params)
        response.raise_for_status()
        return response.json()

    def list_all_shipments(self, **filters) -> List[Dict[str, Any]]:
        page = 1
        all_data: List[Dict[str, Any]] = []

        while True:
            data = self.list_shipments(page=page, **filters)

            if not data:
                break

            all_data.extend(data)

            if len(data) < filters.get("limit", 100):
                break

            page += 1

        return all_data


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def get_unique_skus(line_items: List[Dict[str, Any]]) -> List[str]:
    unique_skus: List[str] = []
    seen = set()

    for item in line_items or []:
        sku = item.get("sku_code")
        if sku:
            sku = str(sku).strip()
            if sku and sku not in seen:
                seen.add(sku)
                unique_skus.append(sku)

    return unique_skus


def split_shipment_into_sku_entries(s: Dict[str, Any]) -> List[Dict[str, Any]]:
    line_items = s.get("line_items", [])
    unique_skus = get_unique_skus(line_items)

    payment_amount = safe_float(s.get("purchase_amount"), 0.0)
    unique_sku_count = len(unique_skus)

    rows: List[Dict[str, Any]] = []

    # If no SKU exists, still keep one row so nothing gets lost
    if unique_sku_count == 0:
        rows.append({
            "shipment_id": s.get("id"),
            "order_id": s.get("order_id"),
            "order_store": s.get("order_store"),
            "Title": s.get("description"),
            "status": s.get("status"),
            "created_at": s.get("created_at"),
            "ship_date": s.get("ship_date"),
            "tracking_code": s.get("carrier_tracking_code"),
            "carrier": s.get("carrier"),
            "postage_type": s.get("postage_type"),
            "to_name": s.get("to_name"),
            "to_city": s.get("to_city"),
            "to_province": s.get("to_province_code"),
            "to_country": s.get("to_country_code"),
            "currency": s.get("currency"),
            "shipment_payment_amount": round(payment_amount, 2),
            "allocated_sku": "",
            "unique_sku_count": 0,
            "allocated_shipping_amount": round(payment_amount, 2),
            "allocation_method": "no_sku_found",
        })
        return rows

    split_amount = round(payment_amount / unique_sku_count, 2)

    # To make sure total stays exact after rounding
    allocated_total = 0.0

    for i, sku in enumerate(unique_skus):
        if i == unique_sku_count - 1:
            allocated_amount = round(payment_amount - allocated_total, 2)
        else:
            allocated_amount = split_amount
            allocated_total += allocated_amount

        rows.append({
            "shipment_id": s.get("id"),
            "order_id": s.get("order_id"),
            "order_store": s.get("order_store"),
            "Title": s.get("description").removeprefix("1 "),
            "status": s.get("status"),
            "created_at": s.get("created_at"),
            "ship_date": s.get("ship_date"),
            "tracking_code": s.get("carrier_tracking_code"),
            "carrier": s.get("carrier"),
            "postage_type": s.get("postage_type"),
            "to_name": s.get("to_name"),
            "to_city": s.get("to_city"),
            "to_province": s.get("to_province_code"),
            "to_country": s.get("to_country_code"),
            "currency": s.get("currency"),
            "shipment_payment_amount": round(payment_amount, 2),
            "allocated_sku": sku,
            "unique_sku_count": unique_sku_count,
            "allocated_shipping_amount": allocated_amount,
            "allocation_method": "equal_by_unique_sku",
        })

    return rows


def flatten_shipments_to_sku_expense_rows(shipments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    all_rows: List[Dict[str, Any]] = []

    for shipment in shipments:
        split_rows = split_shipment_into_sku_entries(shipment)
        all_rows.extend(split_rows)

    return all_rows


def export_to_csv(rows: List[Dict[str, Any]], filename: str) -> None:
    if not rows:
        print("No data to export.")
        return

    fieldnames = list(rows[0].keys())

    with open(filename, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} rows -> {filename}")


def main(): # retrieve your Chit Chats token from the config file
    my_client_id = ""
    access_token = ""
    client_id = my_client_id
    token = access_token

    api = ChitChatsClient(client_id, token)

    shipments = api.list_all_shipments(
        limit=100,
        from_date="2025-01-01",
        # to_date = "2025-12-31"
        to_date= "datetime.now(timezone.utc)"
        # status="ready",
    )

    print(f"Fetched {len(shipments)} shipments")

    expense_rows = flatten_shipments_to_sku_expense_rows(shipments)
    filename = f"chitchats_shipping_log.csv"
    export_to_csv(expense_rows, filename)


if __name__ == "__main__":
    main()

    