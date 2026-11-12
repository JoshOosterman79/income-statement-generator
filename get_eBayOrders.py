import pandas as pd

def get_eBayOrders(data, path):
    keys = path.split(".")


    current = [data]

    for key in keys:
        next_level = []
        for item in current:
            if isinstance(item, dict):
                val = item.get(key)
                if val is not None:
                    next_level.append(val)
            elif isinstance(item, list):
                for sub in item:
                    if isinstance(sub, dict) and key in sub:
                        next_level.append(sub[key])
        current = next_level

    results = []
    for val in current:
        if isinstance(val, list):
            results.extend(val)
        else:
            results.append(val)

    number_values = []

    for n in results:
        try:
            number_values.append(float(n))
        except(TypeError, ValueError):
            pass


    if number_values and len(number_values) == len(results):
        return sum(number_values)
    
    if len(results) == 1:
        return results[0]
    
    return results


    



