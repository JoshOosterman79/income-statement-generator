
import requests
import json
from get_eBayOrders import get_eBayOrders
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

#Enter access token here
access_token = ''


end_date = datetime.now(timezone.utc)
start_date = end_date - timedelta(days=60)
# start_date = datetime(2026, 8, 31, 23, 59, 59, tzinfo=timezone.utc) 
# end_date   = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)


DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
str_start_date = start_date.strftime(DATE_FORMAT)
str_end_date = end_date.strftime(DATE_FORMAT)


def parse_eBayTimeValue(value):
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


# Get API 

url = (
"https://api.ebay.com/sell/fulfillment/v1/order?"
f"filter=creationdate:[{str_start_date}..{str_end_date}]"
)


headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    }


params = {"limit": 200}

response = requests.get(url, headers=headers, params=params)
# response.raise_for_status()
print(response.status_code)
print(response.text)
data = response.json()



orders = data.get("orders", [])

rows = []



for order in orders:
    
    order_id = get_eBayOrders(order, "legacyOrderId")
    creationDate = get_eBayOrders(order, "creationDate")
    parse_time = parse_eBayTimeValue(creationDate)
    sub_total = get_eBayOrders(order, "pricingSummary.total.value")
    totalFee = get_eBayOrders(order, "totalMarketplaceFee.value")
    buyer_username = get_eBayOrders(order, "buyer.username")
    payout_amount = get_eBayOrders(order, "paymentSummary.totalDueSeller.value")

    refund_amount = 0

    if get_eBayOrders(order, "orderPaymentStatus") == "FULLY_REFUNDED":
        for refund in order.get("paymentSummary", {}).get("refunds", []):
            refund_amount = get_eBayOrders(refund, "amount.value")


    for item in order.get("lineItems", []):
        discount_price = get_eBayOrders(
            item,
            "discountedLineItemCost.value"
        )
        if not discount_price:
            discount_price = 0
        lineItem_id = get_eBayOrders(item, "lineItemId")
        sku = get_eBayOrders(item, "sku")
        title = get_eBayOrders(item, "title")
        lineItem_value = get_eBayOrders(item, "total.value")
        lineItem_quantity = get_eBayOrders(item, "quantity")
        len_order = len(order["lineItems"])


# "orderPaymentStatus": "FULLY_REFUNDED"


        discount_amount = 0

        for promotion in item.get("appliedPromotions", []):
            promotion_amount = get_eBayOrders(
                promotion,
                "discountAmount.value"
            )
            if promotion_amount is not None:
                discount_amount += float(promotion_amount)


        rows.append({
            "Creation Date": parse_time,
            "Order Id": order_id,
            "Buyer Username": buyer_username,
            "Sub Total": sub_total,
            "Total Marketplace Fee": totalFee,
            "Refund Amount": refund_amount,
            "Payout Amount": payout_amount,
            "Discounted Price": discount_price,
            "Discount Amount": discount_amount,
            "Line Item Id": lineItem_id,
            "sku": sku,
            "Title": title,
            "Line Item Cost": lineItem_value,
            "Line Item Quantity": lineItem_quantity,
            "Length Order": len_order
        })
            
columns = [
    "Creation Date",
    "Order Id",
    "Sub Total",
    "Total Marketplace Fee",
    "Payout Amount",
    "Refund Amount",
    "Buyer Username",
    "Discounted Price",
    "Discount Amount",
    "Line Item Id",
    "sku", 
    "Title",
    "Line Item Cost",
    "Line Item Quantity",
    "Length Order"
]


csv_path = Path("ebay_finances.csv")

new_df = pd.DataFrame(rows, columns=columns)

# new_df = new_df.drop_duplicates(
#     subset=["Order Id"],
#     keep="last"
# )

if csv_path.exists():
    existing_df = pd.read_csv(csv_path)

    combined_df = pd.concat(
        [existing_df, new_df],
        ignore_index=True
    )

else:
    combined_df = new_df

# combined_df = combined_df.drop_duplicates(
#     subset=["Order Id"],
#     keep="last"
# )

combined_df.drop_duplicates(
    subset=["Order Id", "Line Item Id"]
)

print(combined_df.columns)


combined_df['Creation Date'] = pd.to_datetime(combined_df['Creation Date'], errors='coerce')
combined_df['Creation Date'] = combined_df['Creation Date'].dt.strftime("%Y-%m-%d  %H:%M:%S")


combined_df.to_csv("ebay_finances.csv", columns=columns, index=None)
combined_df = list(combined_df.itertuples(index=False, name=None))
insert_orders(combined_df)


# combined_df.to_csv(
#     csv_path,
#     columns=columns,
#     index=False
# )


existing_count = len(existing_df) if csv_path.exists() else 0
final_count = len(combined_df)


# df = pd.DataFrame(rows)

# df = df.drop_duplicates(subset=["Order Id"], keep="first")


# with open("finances.json", "w") as f:
#     json.dump(data, f, indent=3)
# df.to_csv("ebay_finances.csv", columns=columns, index=False)





