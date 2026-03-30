# 3_harmonic_analysis.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cleaned_data import get_mumbai_cleaned, get_delhi_cleaned, get_dehradun_cleaned, get_jodhpur_cleaned
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Load data
mumbai = get_mumbai_cleaned()
delhi = get_delhi_cleaned()
dehradun = get_dehradun_cleaned()
jodhpur = get_jodhpur_cleaned()

cities = {'Mumbai': mumbai, 'Delhi': delhi, 'Dehradun': dehradun, 'Jodhpur': jodhpur}

print("Harmonic (Fourier) Analysis")
print("="*40)

results_dir = os.path.join(os.path.dirname(__file__), 'results')
os.makedirs(results_dir, exist_ok=True)

fig, axes = plt.subplots(2, 2, figsize=(14, 8))
axes = axes.flatten()

for idx, (city, data) in enumerate(cities.items()):
    data = data.copy()
    data['DATE'] = pd.to_datetime(data['DATE'])
    data = data.sort_values('DATE')
    
    temp = data['TEMP_C'].dropna().values
    n = len(temp)
    
    fft_vals = np.fft.fft(temp)
    freqs = np.fft.fftfreq(n)
    
    power = np.abs(fft_vals)**2
    
    axes[idx].plot(freqs[1:n//2], power[1:n//2])
    axes[idx].set_title(f'{city} - Power Spectrum')
    axes[idx].set_xlabel('Frequency (1/day)')
    axes[idx].set_ylabel('Power')
    axes[idx].grid(True)

plt.tight_layout()
plt.savefig(os.path.join(results_dir, 'harmonic_analysis.png'))
plt.close(fig)
