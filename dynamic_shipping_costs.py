import pandas as pd
from pathlib import Path


current_folder = Path(__file__).parent



data_folder = current_folder / "raw_files" / "supplies_calculations_project.xlsx"


read_excel = pd.read_excel(
    data_folder,
    sheet_name="supplies_table"
)


df = pd.DataFrame(read_excel)

supplies_table = dict(zip(df["Expense Name"], df["Cost"]))



def determine_expense_flag(card_count, max_item_price):
    # a fixed cost representing extra cards
    penny_sleeves = 0.025
 
    if card_count == 1:
        if max_item_price < 20:
            return round(supplies_table["simple_1"],2)
        elif max_item_price < 30:
            return round(supplies_table["simple_2"],2)
        else:
            return round(supplies_table["simple_3"], 2)

    elif card_count == 2:
        if max_item_price < 20:
            return round(supplies_table["duo_1"],2)
        elif max_item_price < 30:
            return round(supplies_table["duo_2"], 2)
        else:
            return round(supplies_table["duo_3"], 2)

    elif card_count > 2 <5:
        if max_item_price < 20:
            return round(supplies_table["multi_1"],2) + card_count*penny_sleeves
        else:
            return round(supplies_table["multi_2"],2) + card_count*penny_sleeves
    
    elif card_count > 5:
        if max_item_price < 20:
            return round(supplies_table["multi_3"], 2) + card_count*penny_sleeves
        else:
            return round(supplies_table["multi_4"], 2) + card_count*penny_sleeves
    return None


