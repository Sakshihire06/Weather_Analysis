import os
import sys
import pandas as pd

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_path not in sys.path:
    sys.path.append(root_path)

from cleaned_data.mumbai_cleaned import get_cleaned_data as get_mumbai
from cleaned_data.delhi_cleaned import get_cleaned_data as get_delhi
from cleaned_data.dehradun_cleaned import get_cleaned_data as get_dehradun
from cleaned_data.jodhpur_cleaned import get_cleaned_data as get_jodhpur

def load_all_cities():
    mumbai   = get_mumbai()
    delhi    = get_delhi()
    dehradun = get_dehradun()
    jodhpur  = get_jodhpur()

    mumbai["CITY"]   = "Mumbai"
    delhi["CITY"]    = "Delhi"
    dehradun["CITY"] = "Dehradun"
    jodhpur["CITY"]  = "Jodhpur"

    all_cities = pd.concat([mumbai, delhi, dehradun, jodhpur], ignore_index=True)
    return all_cities

if __name__ == "__main__":
    df = load_all_cities()
    print(df.head())
