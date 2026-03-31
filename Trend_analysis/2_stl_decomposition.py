# 2_stl_decomposition.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cleaned_data import get_mumbai_cleaned, get_delhi_cleaned, get_dehradun_cleaned, get_jodhpur_cleaned
from statsmodels.tsa.seasonal import STL
import pandas as pd
import matplotlib.pyplot as plt

# Load data
mumbai = get_mumbai_cleaned()
delhi = get_delhi_cleaned()
dehradun = get_dehradun_cleaned()
jodhpur = get_jodhpur_cleaned()

cities = {'Mumbai': mumbai, 'Delhi': delhi, 'Dehradun': dehradun, 'Jodhpur': jodhpur}

print("STL Decomposition Analysis - 2_stl_decomposition.py:19")
print("= - 2_stl_decomposition.py:20"*40)

results_dir = os.path.join(os.path.dirname(__file__), 'results')
os.makedirs(results_dir, exist_ok=True)

fig, axes = plt.subplots(4, 3, figsize=(15, 12))

for idx, (city, data) in enumerate(cities.items()):
    data = data.copy()
    data['DATE'] = pd.to_datetime(data['DATE'])
    data = data.set_index('DATE').asfreq('D')
    data['TEMP_C'] = data['TEMP_C'].interpolate()
    
    stl = STL(data['TEMP_C'].dropna(), period=365, robust=True)
    result = stl.fit()
    
    axes[idx, 0].plot(result.trend)
    axes[idx, 0].set_title(f'{city} - Trend')
    axes[idx, 1].plot(result.seasonal)
    axes[idx, 1].set_title(f'{city} - Seasonal')
    axes[idx, 2].plot(result.resid)
    axes[idx, 2].set_title(f'{city} - Residual')

plt.tight_layout()
plt.show()
plt.savefig(os.path.join(results_dir, 'stl_decomposition.png'))
plt.close(fig)
