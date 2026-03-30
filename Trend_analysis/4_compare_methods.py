# 4_compare_methods.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cleaned_data import get_mumbai_cleaned, get_delhi_cleaned, get_dehradun_cleaned, get_jodhpur_cleaned
import pandas as pd
import numpy as np

# Load data
mumbai = get_mumbai_cleaned()
delhi = get_delhi_cleaned()
dehradun = get_dehradun_cleaned()
jodhpur = get_jodhpur_cleaned()

all_cities = pd.concat([mumbai, delhi, dehradun, jodhpur], ignore_index=True)
all_cities['DATE'] = pd.to_datetime(all_cities['DATE'])

results_dir = os.path.join(os.path.dirname(__file__), 'results')
os.makedirs(results_dir, exist_ok=True)

print("Method Comparison Summary")
print("="*40)

comparison = []

for city in all_cities['CITY'].unique():
    city_data = all_cities[all_cities['CITY'] == city].sort_values('DATE')
    original_std = city_data['TEMP_C'].std()
    
    rolling_30d_std = city_data['TEMP_C'].rolling(window=30, center=True).mean().std()
    
    reduction = (original_std - rolling_30d_std) / original_std * 100
    
    comparison.append({
        'City': city,
        'Original STD (C)': round(original_std, 2),
        'Rolling 30d STD (C)': round(rolling_30d_std, 2),
        'Noise Reduction (%)': round(reduction, 1)
    })

comparison_df = pd.DataFrame(comparison)
print(comparison_df.to_string(index=False))

output_path = os.path.join(results_dir, 'method_comparison.csv')
comparison_df.to_csv(output_path, index=False)
print(f"\nResults saved to {output_path}")
