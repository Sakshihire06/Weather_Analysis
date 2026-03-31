# 1_rolling_average.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cleaned_data import get_mumbai_cleaned, get_delhi_cleaned, get_dehradun_cleaned, get_jodhpur_cleaned
import pandas as pd
import matplotlib.pyplot as plt

# Load data
mumbai = get_mumbai_cleaned()
delhi = get_delhi_cleaned()
dehradun = get_dehradun_cleaned()
jodhpur = get_jodhpur_cleaned()

all_cities = pd.concat([mumbai, delhi, dehradun, jodhpur], ignore_index=True)
all_cities['DATE'] = pd.to_datetime(all_cities['DATE'])

results_dir = os.path.join(os.path.dirname(__file__), 'results')
os.makedirs(results_dir, exist_ok=True)

print("Rolling Average Analysis")
print("="*40)

windows = [7, 30, 90]
fig, axes = plt.subplots(2, 2, figsize=(14, 8))
axes = axes.flatten()

for idx, city in enumerate(all_cities['CITY'].unique()):
    city_data = all_cities[all_cities['CITY'] == city].sort_values('DATE')
    
    for w in windows:
        city_data[f'rolling_{w}d'] = city_data['TEMP_C'].rolling(window=w, center=True).mean()
        print(f"{city} - {w} day window: STD reduced by {((city_data['TEMP_C'].std() - city_data[f'rolling_{w}d'].std())/city_data['TEMP_C'].std()*100):.1f}%")
    
    axes[idx].plot(city_data['DATE'], city_data['TEMP_C'], alpha=0.3, label='Original')
    axes[idx].plot(city_data['DATE'], city_data['rolling_30d'], 'r-', label='30-day rolling')
    axes[idx].set_title(city)
    axes[idx].legend()
    axes[idx].grid(True)

plt.tight_layout()
plt.show()
plt.savefig(os.path.join(results_dir, 'rolling_average.png'))
plt.close(fig)
