
import pandas as pd

from cleaned_data import (
    get_mumbai_cleaned,
    get_delhi_cleaned,
    get_dehradun_cleaned,
    get_jodhpur_cleaned
)

def load_all_cities():
    mumbai   = get_mumbai_cleaned()
    delhi    = get_delhi_cleaned()
    dehradun = get_dehradun_cleaned()
    jodhpur  = get_jodhpur_cleaned()

    mumbai["CITY"] = "Mumbai"
    delhi["CITY"] = "Delhi"
    dehradun["CITY"] = "Dehradun"
    jodhpur["CITY"] = "Jodhpur"

    
    all_cities = pd.concat([mumbai, delhi, dehradun, jodhpur], ignore_index=True)

    return all_cities


if __name__ == "__main__":
    df = load_all_cities()
    print(df.head())
    print(df.info())