# rolling_mean_analysis.py
import pandas as pd
import matplotlib.pyplot as plt

def calculate_rolling_means(input_file='dummy_weather_data.csv', window=30):
    """
    Calculate rolling mean for temperature data
    
    Parameters:
    - input_file: CSV file with weather data
    - window: Rolling window size in days
    """
    
    # Load data
    df = pd.read_csv(input_file)
    df['DATE'] = pd.to_datetime(df['DATE'])
    
    print("ROLLING MEAN ANALYSIS")
    print(f"Window size: {window} days")
    print(f"Cities: {df['CITY'].unique().tolist()}")
    
    # Calculate rolling mean for each city
    results = []
    
    for city in df['CITY'].unique():
        city_data = df[df['CITY'] == city].copy().sort_values('DATE')
        
        # Calculate rolling mean
        city_data['TEMP_ROLLING'] = city_data['TEMP'].rolling(
            window=window, center=True, min_periods=1
        ).mean()
        
        # Calculate rolling std deviation
        city_data['TEMP_ROLLING_STD'] = city_data['TEMP'].rolling(
            window=window, center=True, min_periods=1
        ).std()
        
        results.append(city_data)
        
        # Print statistics
        print(f"\n{city}:")
        print(f"   Original temp range: {city_data['TEMP'].min():.1f}C to {city_data['TEMP'].max():.1f}C")
        print(f"   Rolling mean range: {city_data['TEMP_ROLLING'].min():.1f}C to {city_data['TEMP_ROLLING'].max():.1f}C")
        print(f"   Smoothing effect: {city_data['TEMP'].std():.2f}C -> {city_data['TEMP_ROLLING'].std():.2f}C")
    
    # Combine results
    result_df = pd.concat(results, ignore_index=True)
    
    # Save results
    result_df.to_csv('rolling_mean_results.csv', index=False)
    print(f"\nResults saved to: rolling_mean_results.csv")
    
    # Quick visualization
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    for idx, city in enumerate(df['CITY'].unique()):
        city_data = result_df[result_df['CITY'] == city]
        
        axes[idx].plot(city_data['DATE'], city_data['TEMP'], alpha=0.5, linewidth=0.8, label='Original')
        axes[idx].plot(city_data['DATE'], city_data['TEMP_ROLLING'], 'r-', linewidth=2, label=f'{window}-day rolling')
        axes[idx].fill_between(city_data['DATE'],
                               city_data['TEMP_ROLLING'] - city_data['TEMP_ROLLING_STD'],
                               city_data['TEMP_ROLLING'] + city_data['TEMP_ROLLING_STD'],
                               alpha=0.2, color='red')
        axes[idx].set_title(city)
        axes[idx].set_ylabel('Temperature (C)')
        axes[idx].legend()
        axes[idx].grid(True, alpha=0.3)
    
    plt.suptitle(f'Rolling Mean Analysis ({window}-day window)', fontsize=16)
    plt.tight_layout()
    plt.savefig('rolling_mean_plot.png', dpi=150)
    plt.show()
    
    return result_df

def compare_windows(input_file='dummy_weather_data.csv', windows=[7, 30, 90]):
    """Compare different rolling window sizes"""
    
    df = pd.read_csv(input_file)
    df['DATE'] = pd.to_datetime(df['DATE'])
    
    print("\nWINDOW SIZE COMPARISON")
    
    comparison = []
    
    for city in df['CITY'].unique():
        city_data = df[df['CITY'] == city].copy().sort_values('DATE')
        
        print(f"\n{city}:")
        for window in windows:
            rolling = city_data['TEMP'].rolling(window=window, center=True).mean()
            reduction = (city_data['TEMP'].std() - rolling.std()) / city_data['TEMP'].std() * 100
            print(f"   {window}-day: STD reduced by {reduction:.1f}%")
            comparison.append({
                'CITY': city,
                'WINDOW': window,
                'STD_REDUCTION': round(reduction, 1)
            })
    
    # Create comparison table
    comp_df = pd.DataFrame(comparison)
    pivot = comp_df.pivot(index='CITY', columns='WINDOW', values='STD_REDUCTION')
    print("\nStandard Deviation Reduction (%)")
    print(pivot)
    
    return pivot

if __name__ == "__main__":
    # First generate data if needed
    # from generate_dummy_weather import generate_dummy_weather_data
    # generate_dummy_weather_data()
    
    # Run analysis
    df = calculate_rolling_means(window=30)
    
    # Compare different window sizes
    compare_windows(windows=[7, 30, 90])
