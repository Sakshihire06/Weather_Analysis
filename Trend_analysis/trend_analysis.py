# trend_analysis.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cleaned_data import get_mumbai_cleaned, get_delhi_cleaned, get_dehradun_cleaned, get_jodhpur_cleaned
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import STL

def load_all_cities():
    """Load and combine data for all four cities"""
    mumbai = get_mumbai_cleaned()
    delhi = get_delhi_cleaned()
    dehradun = get_dehradun_cleaned()
    jodhpur = get_jodhpur_cleaned()
    
    # Convert TEMP to TEMP_C if needed
    for df in [mumbai, delhi, dehradun, jodhpur]:
        if 'TEMP' in df.columns and 'TEMP_C' not in df.columns:
            df['TEMP_C'] = df['TEMP']
    
    all_cities = pd.concat([mumbai, delhi, dehradun, jodhpur], ignore_index=True)
    all_cities['DATE'] = pd.to_datetime(all_cities['DATE'])
    
    cities_dict = {
        'Mumbai': mumbai,
        'Delhi': delhi,
        'Dehradun': dehradun,
        'Jodhpur': jodhpur
    }
    
    return all_cities, cities_dict

def rolling_average(data, windows=[7, 30, 90], save_plot=True):
    """Compute and plot rolling averages for given data"""
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    print("Rolling Average Analysis")
    print("="*40)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    axes = axes.flatten()
    
    for idx, city in enumerate(data['CITY'].unique()):
        city_data = data[data['CITY'] == city].sort_values('DATE').copy()
        
        for w in windows:
            col = f'rolling_{w}d'
            city_data[col] = city_data['TEMP_C'].rolling(window=w, center=True).mean()
            reduction = ((city_data['TEMP_C'].std() - city_data[col].std()) / city_data['TEMP_C'].std() * 100)
            print(f"{city} - {w} day window: STD reduced by {reduction:.1f}%")
        
        axes[idx].plot(city_data['DATE'], city_data['TEMP_C'], alpha=0.3, label='Original')
        axes[idx].plot(city_data['DATE'], city_data['rolling_30d'], 'r-', label='30-day rolling')
        axes[idx].set_title(city)
        axes[idx].legend()
        axes[idx].grid(True)
    
    plt.tight_layout()
    
    if save_plot:
        plt.savefig(os.path.join(results_dir, 'rolling_average.png'))
    plt.show()
    plt.close()
    
    return data

def stl_decomposition(cities_dict, period=365, save_plot=True):
    """
    Perform STL decomposition for each city with error handling
    """
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    print("STL Decomposition Analysis")
    print("="*40)
    
    fig, axes = plt.subplots(4, 3, figsize=(15, 12))
    results = {}
    
    for idx, (city, data) in enumerate(cities_dict.items()):
        print(f"Processing {city}...")
        
        data = data.copy()
        data['DATE'] = pd.to_datetime(data['DATE'])
        data = data.set_index('DATE')
        
        # Ensure daily frequency
        date_range = pd.date_range(start=data.index.min(), end=data.index.max(), freq='D')
        data = data.reindex(date_range)
        data['TEMP_C'] = data['TEMP_C'].interpolate(method='linear')
        
        # Check if we have enough data
        if len(data) < 2 * period:
            print(f"  Warning: {city} has insufficient data for STL with period={period}")
            print(f"  Using period={period//2} instead")
            period_used = period // 2
        else:
            period_used = period
        
        try:
            stl = STL(data['TEMP_C'].dropna(), period=period_used, robust=True)
            result = stl.fit()
            results[city] = result
            
            axes[idx, 0].plot(result.trend)
            axes[idx, 0].set_title(f'{city} - Trend')
            axes[idx, 1].plot(result.seasonal)
            axes[idx, 1].set_title(f'{city} - Seasonal')
            axes[idx, 2].plot(result.resid)
            axes[idx, 2].set_title(f'{city} - Residual')
            
            print(f"  {city} - STL completed successfully")
            
        except Exception as e:
            print(f"  Error with {city}: {e}")
            # Fallback: simple moving average as trend
            axes[idx, 0].plot(data['TEMP_C'].rolling(window=30).mean(), color='orange')
            axes[idx, 0].set_title(f'{city} - Trend (rolling avg fallback)')
            axes[idx, 1].plot([0], [0])
            axes[idx, 1].set_title(f'{city} - Seasonal (not available)')
            axes[idx, 2].plot([0], [0])
            axes[idx, 2].set_title(f'{city} - Residual (not available)')
    
    plt.tight_layout()
    
    if save_plot:
        plt.savefig(os.path.join(results_dir, 'stl_decomposition.png'))
    plt.show()
    plt.close()
    
    return results

def harmonic_reconstruction(data, n_harmonics):
    """Reconstruct signal using only first n_harmonics"""
    fft_vals = np.fft.fft(data)
    fft_copy = fft_vals.copy()
    
    n = len(data)
    for i in range(n):
        freq = i if i <= n//2 else i - n
        if abs(freq) > n_harmonics:
            fft_copy[i] = 0
    
    return np.fft.ifft(fft_copy).real

def harmonic_analysis(cities_dict, harmonics=[1, 2, 5], save_plot=True):
    """Perform harmonic reconstruction analysis"""
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    print("Harmonic Analysis - Progressive Reconstruction")
    print("="*60)
    
    fig, axes = plt.subplots(4, len(harmonics) + 1, figsize=(16, 12))
    fig.suptitle('Harmonic Reconstruction of Temperature Data', fontsize=14)
    
    for idx, (city, data) in enumerate(cities_dict.items()):
        print(f"Processing {city}...")
        
        data = data.copy()
        data['DATE'] = pd.to_datetime(data['DATE'])
        data = data.sort_values('DATE')
        
        temp = data['TEMP_C'].dropna().values
        
        # Original (column 0)
        axes[idx, 0].plot(temp, 'k-', linewidth=1)
        axes[idx, 0].set_title(f'{city} - Original')
        axes[idx, 0].set_ylabel('Temperature (°C)')
        
        # Reconstruct with harmonics
        for j, h in enumerate(harmonics):
            col = j + 1
            recon = harmonic_reconstruction(temp, h)
            axes[idx, col].plot(temp, 'gray', alpha=0.3, linewidth=0.5)
            axes[idx, col].plot(recon, 'r-', linewidth=1.5)
            axes[idx, col].set_title(f'{h} harmonic(s)')
            
            variance_explained = 1 - np.var(temp - recon) / np.var(temp)
            print(f"  {city} - {h} harmonic(s): {variance_explained:.1%} variance explained")
    
    for j in range(len(harmonics) + 1):
        axes[-1, j].set_xlabel('Days')
    
    plt.tight_layout()
    
    if save_plot:
        plt.savefig(os.path.join(results_dir, 'harmonic_reconstruction.png'))
    plt.show()
    plt.close()

def compare_methods(data, save_csv=True):
    """Compare different smoothing methods"""
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    print("Method Comparison Summary")
    print("="*40)
    
    comparison = []
    
    for city in data['CITY'].unique():
        city_data = data[data['CITY'] == city].sort_values('DATE')
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
    
    if save_csv:
        output_path = os.path.join(results_dir, 'method_comparison.csv')
        comparison_df.to_csv(output_path, index=False)
        print(f"\nResults saved to {output_path}")
    
    return comparison_df

def run_all_analysis():
    """Run all trend analysis methods"""
    print("="*60)
    print("TREND ANALYSIS MODULE")
    print("="*60)
    
    # Load data
    all_cities, cities_dict = load_all_cities()
    
    # Run all analyses
    rolling_average(all_cities)
    stl_decomposition(cities_dict)
    harmonic_analysis(cities_dict)
    compare_methods(all_cities)
    
    print("\nAll analyses complete!")

# For direct execution
if __name__ == "__main__":
    run_all_analysis()
