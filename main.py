import requests
from datetime import datetime, timedelta, timezone
from dynamic_shipping_costs import determine_expense_flag
import os 
import pandas as pd
from collections import defaultdict
from get_eBayOrders import get_eBayOrders
# from ebay_token.config import access_token


#Enter access token here
access_token = ''



end_date = datetime.now(timezone.utc)
start_date = end_date - timedelta(days=30)
# start_date = datetime(2026, 8, 1, 23, 59, 59, tzinfo=timezone.utc) 
# end_date   = datetime(2026, 8, 29, 0, 0, 0, tzinfo=timezone.utc)
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
str_start_date = start_date.strftime(DATE_FORMAT)
str_end_date = end_date.strftime(DATE_FORMAT)



url = (
"https://api.ebay.com/sell/fulfillment/v1/order?"
f"filter=creationdate:[{str_start_date}..{str_end_date}]"
)


headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    }


params = {"limit": 100}

response = requests.get(url, headers=headers, params=params)

data = response.json()


order_columns = {

"Buyer Username": "buyer.username",

"Order ID": "orderId",

"Creation Date": "creationDate",

"Order Total": "totalFeeBasisAmount.value",

"Shipping Charged": "lineItems.deliveryCost.shippingCost.value",

"Marketplace Fee": "totalMarketplaceFee.value"

}

  

item_columns = {

"Line Item ID": "lineItemId",

"SKU": "sku",

"Title": "title",

"Quantity": "quantity",

"Item Price": "lineItemCost.value"

}

def parse_eBayTimeValue(value):
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def split_supplies_cost_even(total_amount, n):
    if total_amount is None or n <= 0:
        return [None] * n
    total_amount = round(float(total_amount),2)
    base_average = round(total_amount / n, 2)
    amounts = [base_average] * n

    sum_of_amounts = round(sum(amounts),2)
    diff = round(total_amount - sum_of_amounts, 2)
    amounts[-1] = round(amounts[-1] - diff, 2)

    return amounts

def export_orders_to_csv(data, order_columns, item_columns, filename="orders.csv"):
    
    orders = data.get("orders", [])
    if not orders:
        print("Orders Not Found")
        return 
    
    rows = []
    order_keys = set()
    buyer_windows_written = set() 

    if os.path.exists(filename):
        existing_df = pd.read_csv(
            filename,
            usecols=[
            "Order ID",
            "Line Item ID",
            "Buyer Username",
            "Buyer 24h Card Count Anchor"]
        )

        order_keys = set(
            zip(
                existing_df["Order ID"].astype(str),
                existing_df["Line Item ID"].astype(str)
            )
        )
        buyer_windows_written = set(
            zip(
                existing_df["Buyer Username"].astype(str),
                existing_df["Buyer 24h Card Count Anchor"].astype(str)
            )
        )


    buyer_orders = defaultdict(list)

    for order in orders:
        buyer = get_eBayOrders(order, "buyer.username")
        creation_date = get_eBayOrders(order, "creationDate")
        order_time = parse_eBayTimeValue(creation_date)
        buyer_orders[buyer].append((order_time, order))

    for buyer in buyer_orders:
        buyer_orders[buyer].sort(key=lambda x: x[0])

    
    buyer_windows = []

    for buyer, entries in buyer_orders.items():
        window = []
        window_start = None

        for order_time, order in entries:
            if not window:
                window = [(order_time, order)]
                window_start = order_time
                continue

            if order_time - window_start <= timedelta(hours=24):
                window.append((order_time, order))
            else:
                buyer_windows.append((buyer, window))
                window = [(order_time, order)]
                window_start = order_time

        if window:
            buyer_windows.append((buyer, window))

    # get the Buyer's window Order Total, Length of Order, Fee Total, and Shipping total
    for buyer, window in buyer_windows:
        total_cards = sum(len(order.get("lineItems", [])) for _, order in window)
        anchor_order_id = str(get_eBayOrders(window[0][1], "orderId"))
        window_key = (buyer, anchor_order_id)
        helper_written = window_key in buyer_windows_written


        window_order_total = 0.0
        window_fee_total = 0.0
        shipping_total = 0.0

        for _, order in window:
            shipping = get_eBayOrders(order, "lineItems.deliveryCost.shippingCost.value")
            try:
                shipping_total += float(shipping)
            except (TypeError, ValueError):
                pass
            fees = get_eBayOrders(order, "totalMarketplaceFee.value")
            try:
                window_fee_total += float(fees)
            except (TypeError, ValueError):
                pass
            for li in order.get("lineItems", []):
                price = get_eBayOrders(li, "lineItemCost.value")
                try:
                    price = float(price)
                    window_order_total += price
                    # max_price = max(max_price, price)
                except (TypeError, ValueError):
                    pass

        supplies_flag_total = determine_expense_flag(total_cards, window_order_total)

        net_24h = None

        if (total_cards >=1): # make-shift order promo fee is included
            net_24h = round(window_order_total + shipping_total - window_fee_total - supplies_flag_total - (window_order_total*0.021), 2)

        window_rows = []

        for _, order in window:
            order_base = {}

            for col, path in order_columns.items():
                value = get_eBayOrders(order, path)

                if path == "creationDate" and isinstance(value, str):
                    dt = parse_eBayTimeValue(value)
                    value = dt.strftime("%Y-%m-%d %H:%M:%S")

                order_base[col] = value

            for li in order.get("lineItems", []):
                row = order_base.copy()

                for col, path in item_columns.items():
                    value = get_eBayOrders(li, path)
                    if isinstance(value, list):
                        value = value[0] if value else None
                    row[col] = value

                try:
                    price = float(row["Item Price"])
                    row["Sales Tax Allocation"] = round(price * 0.12,2)
                    row["Promo Fee"] = round(price * 0.021,2)
                except (TypeError, ValueError):
                    row["Sales Tax Allocation"] = None
                    row["Promo Fee"] = None

                if not helper_written:
                    row["Buyer 24h Card Count"] = total_cards
                    row["Buyer 24h Card Count Anchor"] = anchor_order_id
                    row["Buyer 24h Order Total"] = round(window_order_total, 2)
                    row["24h Marketplace Fee Total"] = round(window_fee_total,2)
                    row["Expense Flag"] = supplies_flag_total
                    row["Order Net Revenue"] = net_24h

                    helper_written = True
                    buyer_windows_written.add(window_key)

                else:
                    row["Buyer 24h Card Count"] = None
                    row["Buyer 24h Card Count Anchor"] = None
                    row["Buyer 24h Order Total"] = None
                    row["24h Marketplace Fee Total"] = None
                    row["Expense Flag"] = None
                    row["Order Net Revenue"] = None
                
                window_rows.append(row)

        distribute_supplies_flag = split_supplies_cost_even(supplies_flag_total, len(window_rows))


        for idx, row in enumerate(window_rows):
            row["Supplies Flag Allocation"] = distribute_supplies_flag[idx]

        for row in window_rows:
            key = (str(row["Order ID"]), str(row["Line Item ID"]))
            if key in order_keys:
                continue

            order_keys.add(key)
            rows.append(row)
        
    final_columns = (
        list(order_columns.keys()) +
        list(item_columns.keys())
        + [
            "Buyer 24h Card Count",
            "Sales Tax Allocation",
            "Buyer 24h Card Count Anchor",
            "Buyer 24h Order Total",
            "24h Marketplace Fee Total",
            "Promo Fee",
            "Expense Flag",
            "Supplies Flag Allocation",
            "Order Net Revenue",
        ]
    )

    df = pd.DataFrame(rows, columns=final_columns)

    if os.path.exists(filename):
        df.to_csv(filename, mode="a", header=False, index=False)
    else:
        df.to_csv(filename, index=False)

    print(f" Exported {len(df)} rows to {filename}")


# sku_columns = [
#     "sku",
#     "quantity",
#     "item_price"
#     "sales_tax",
#     ""

# ]


export_orders_to_csv(data, order_columns, item_columns, "orders.csv")

    
        





    
            


        





    











        

    





    










    









    

