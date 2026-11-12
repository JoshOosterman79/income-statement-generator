import os
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone




#Enter access token here
access_token = ''


# =========================
# CONFIG
# =========================
OUTPUT_CSV = "ebay_shipping_labels.csv"
LOOKBACK_DAYS = 180
MARKETPLACE_ID = "EBAY_CA"


FINANCES_URL = "https://apiz.ebay.com/sell/finances/v1/transaction"
FULFILLMENT_URL = "https://api.ebay.com/sell/fulfillment/v1/order"


headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE_ID,
}

# =========================
# DATE HELPERS
# =========================
def to_ebay_time(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


end_date = datetime.now(timezone.utc) - timedelta(minutes=5)
start_date = end_date - timedelta(days=LOOKBACK_DAYS)

str_start_date = to_ebay_time(start_date)
str_end_date = to_ebay_time(end_date)

print("Fetching shipping label transactions for range:")
print("START:", str_start_date)
print("END:  ", str_end_date)

# =========================
# HELPERS
# =========================
order_cache = {}


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def split_amount_evenly(total_amount: float, count: int):
    """
    Split a dollar amount evenly across count entries while preserving total.
    Returns a list rounded to 2 decimals that sums exactly to total_amount.
    Example: 10 / 3 -> [3.34, 3.33, 3.33]
    """
    if count <= 0:
        return []

    total_cents = int(round(total_amount * 100))
    base = total_cents // count
    remainder = total_cents % count

    values = []
    for i in range(count):
        cents = base + (1 if i < remainder else 0)
        values.append(cents / 100)

    return values


def get_order_details(order_id: str) -> dict:
    """
    Fetch order details and return:
    - order creation date
    - split rows by unique SKU
    """
    if not order_id:
        return {
            "order_creation_date": None,
            "sku_rows": [],
        }

    if order_id in order_cache:
        return order_cache[order_id]

    url = f"{FULFILLMENT_URL}/{order_id}"

    try:
        resp = requests.get(url, headers=headers, timeout=30)

        if resp.status_code == 404:
            result = {
                "order_creation_date": None,
                "sku_rows": [],
            }
            order_cache[order_id] = result
            return result

        resp.raise_for_status()
        data = resp.json()

        line_items = data.get("lineItems", [])
        sku_map = {}

        for item in line_items:
            sku = item.get("sku")
            title = item.get("title")
            quantity = item.get("quantity")

            if sku is None or not str(sku).strip():
                continue

            sku = str(sku).strip()

            if sku not in sku_map:
                sku_map[sku] = {
                    "SKU": sku,
                    "Title": str(title).strip() if title else None,
                    "Order Quantity": safe_float(quantity) if quantity is not None else None,
                }

        result = {
            "order_creation_date": data.get("creationDate"),
            "sku_rows": list(sku_map.values()),
        }
        order_cache[order_id] = result
        return result

    except requests.RequestException as e:
        print(f"Could not fetch order {order_id}: {e}")
        result = {
            "order_creation_date": None,
            "sku_rows": [],
        }
        order_cache[order_id] = result
        return result


def build_row_key(row: dict) -> str:
    """
    Unique key per output row.
    Since one transaction can split into multiple SKU rows,
    use Transaction ID + SKU.
    """
    tx_id = str(row.get("Transaction ID") or "").strip()
    sku = str(row.get("SKU") or "").strip()
    return f"{tx_id}||{sku}"


# =========================
# FETCH SHIPPING LABELS
# =========================
def fetch_shipping_label_transactions(existing_keys=None):
    if existing_keys is None:
        existing_keys = set()

    rows = []
    limit = 200
    offset = 0

    filters = [
        "transactionType:{SHIPPING_LABEL}",
        f"transactionDate:[{str_start_date}..{str_end_date}]"
    ]

    while True:
        params = {
            "filter": ",".join(filters),
            "limit": limit,
            "offset": offset,
        }

        print(f"Fetching transactions offset={offset} ...")
        resp = requests.get(FINANCES_URL, headers=headers, params=params, timeout=30)

        if resp.status_code == 204:
            print("No content returned.")
            break

        resp.raise_for_status()
        data = resp.json()

        transactions = data.get("transactions", [])
        if not transactions:
            print("No more transactions found.")
            break

        for tx in transactions:
            order_id = tx.get("orderId")
            amount = tx.get("amount", {}) or {}
            taxes = tx.get("taxes", []) or {}

            label_price = safe_float(amount.get("value"))

            tax_total = 0.0
            tax_currency = None

            if isinstance(taxes, list):
                for tax in taxes:
                    tax_amount = tax.get("amount", {}) or {}
                    tax_total += safe_float(tax_amount.get("value"))
                    if tax_amount.get("currency"):
                        tax_currency = tax_amount.get("currency")

            order_info = get_order_details(order_id)
            sku_rows = order_info.get("sku_rows", [])
            unique_sku_count = len(sku_rows)

            # If no SKU found, still keep one row
            if unique_sku_count == 0:
                row = {
                    "Transaction Date": tx.get("transactionDate"),
                    "Order Creation Date": order_info.get("order_creation_date"),
                    "Order ID": order_id,
                    "Transaction ID": tx.get("transactionId"),
                    "Booking Entry": tx.get("bookingEntry"),
                    "Transaction Status": tx.get("transactionStatus"),
                    "Transaction Memo": tx.get("transactionMemo"),
                    "Buyer Username": (tx.get("buyer") or {}).get("username"),
                    "Payout ID": tx.get("payoutId"),
                    "Label Price": round(label_price, 2),
                    "Currency": amount.get("currency"),
                    "Label Tax": round(tax_total, 2),
                    "Tax Currency": tax_currency or amount.get("currency"),
                    "Unique SKU Count": 0,
                    "SKU": None,
                    "Title": None,
                    "Order Quantity": None,
                    "Allocated Shipping Label Cost": None,
                }

                row_key = build_row_key(row)
                if row_key not in existing_keys:
                    rows.append(row)
                    existing_keys.add(row_key)

                continue

            allocated_costs = split_amount_evenly(label_price, unique_sku_count)

            for sku_row, allocated_cost in zip(sku_rows, allocated_costs):
                row = {
                    "Transaction Date": tx.get("transactionDate"),
                    "Order Creation Date": order_info.get("order_creation_date"),
                    "Order ID": order_id,
                    "Transaction ID": tx.get("transactionId"),
                    "Booking Entry": tx.get("bookingEntry"),
                    "Transaction Status": tx.get("transactionStatus"),
                    "Transaction Memo": tx.get("transactionMemo"),
                    "Buyer Username": (tx.get("buyer") or {}).get("username"),
                    "Payout ID": tx.get("payoutId"),
                    "Label Price": round(label_price, 2),
                    "Currency": amount.get("currency"),
                    "Label Tax": round(tax_total, 2),
                    "Tax Currency": tax_currency or amount.get("currency"),
                    "Unique SKU Count": unique_sku_count,
                    "SKU": sku_row.get("SKU"),
                    "Title": sku_row.get("Title"),
                    "Order Quantity": sku_row.get("Order Quantity"),
                    "Allocated Shipping Label Cost": allocated_cost,
                }

                row_key = build_row_key(row)
                if row_key not in existing_keys:
                    rows.append(row)
                    existing_keys.add(row_key)

        if len(transactions) < limit:
            break

        offset += limit

    return rows


# =========================
# LOAD EXISTING CSV
# =========================
def load_existing_data(columns):
    if not os.path.exists(OUTPUT_CSV):
        return pd.DataFrame(columns=columns), set()

    try:
        existing_df = pd.read_csv(OUTPUT_CSV, dtype=str, encoding="utf-8-sig")
        existing_df = existing_df.reindex(columns=columns)

        # Convert numeric columns back if desired
        numeric_cols = [
            "Label Price",
            "Label Tax",
            "Unique SKU Count",
            "Order Quantity",
            "Allocated Shipping Label Cost",
        ]
        for col in numeric_cols:
            if col in existing_df.columns:
                existing_df[col] = pd.to_numeric(existing_df[col], errors="coerce")

        existing_keys = set()
        for _, row in existing_df.iterrows():
            existing_keys.add(
                build_row_key({
                    "Transaction ID": row.get("Transaction ID"),
                    "SKU": row.get("SKU"),
                })
            )

        print(f"Loaded existing CSV with {len(existing_df)} rows.")
        return existing_df, existing_keys

    except Exception as e:
        print(f"Could not read existing CSV, starting fresh. Reason: {e}")
        return pd.DataFrame(columns=columns), set()


# =========================
# MAIN
# =========================
def main():
    columns = [
        "Transaction Date",
        "Order Creation Date",
        "Order ID",
        "Transaction ID",
        "Booking Entry",
        "Transaction Status",
        "Transaction Memo",
        "Buyer Username",
        "Payout ID",
        "Label Price",
        "Currency",
        "Label Tax",
        "Tax Currency",
        "Unique SKU Count",
        "SKU",
        "Title",
        "Order Quantity",
        "Allocated Shipping Label Cost",
    ]

    try:
        existing_df, existing_keys = load_existing_data(columns)
        new_rows = fetch_shipping_label_transactions(existing_keys=existing_keys)

        if new_rows:
            new_df = pd.DataFrame(new_rows, columns=columns)
            final_df = pd.concat([existing_df, new_df], ignore_index=True)
            print(f"Appending {len(new_df)} new rows.")
        else:
            final_df = existing_df.copy()
            print("No new rows to append.")

        # final safety de-duplication
        final_df["_row_key"] = final_df.apply(
            lambda r: build_row_key({
                "Transaction ID": r.get("Transaction ID"),
                "SKU": r.get("SKU"),
            }),
            axis=1
        )
        final_df = final_df.drop_duplicates(subset=["_row_key"], keep="first").drop(columns=["_row_key"])

        final_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        print(f"Saved {len(final_df)} total rows to {OUTPUT_CSV}")

    except requests.HTTPError as e:
        print("HTTP error occurred.")
        print("Status code:", e.response.status_code if e.response else "Unknown")
        print("Response text:", e.response.text if e.response else str(e))
    except Exception as e:
        print("Unexpected error:", str(e))


if __name__ == "__main__":
    main()