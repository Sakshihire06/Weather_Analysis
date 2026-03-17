# generate_dummy_weather.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_dummy_weather_data():
    """Generate realistic dummy weather data for 4 Indian cities"""
    
    # City configurations
    cities = {
        'Mumbai': {'base_temp': 27, 'amplitude': 5, 'rainy': True},
        'Delhi': {'base_temp': 25, 'amplitude': 15, 'rainy': True},
        'Dehradun': {'base_temp': 20, 'amplitude': 12, 'rainy': True},
        'Jodhpur': {'base_temp': 28, 'amplitude': 14, 'rainy': False}
    }
    
    # Generate daily data for 2 years (2023-2024)
    start_date = datetime(2023, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(730)]  # 2 years
    
    data = []
    np.random.seed(42)  # For reproducibility
    
    for date in dates:
        month = date.month
        
        for city, config in cities.items():
            # Temperature with seasonal pattern
            seasonal = config['amplitude'] * np.sin(2 * np.pi * (month - 1) / 12)
            daily_variation = np.random.normal(0, 2)
            temp = config['base_temp'] + seasonal + daily_variation
            
            # Precipitation
            if config['rainy'] and month in [6, 7, 8, 9]:  # Monsoon months
                prcp = np.random.exponential(15) if np.random.random() > 0.3 else 0
            else:
                prcp = np.random.exponential(2) if np.random.random() > 0.8 else 0
            
            # Wind speed
            wdsp = np.random.gamma(2, 2) + 5
            
            data.append({
                'DATE': date.strftime('%Y-%m-%d'),
                'CITY': city,
                'TEMP': round(temp, 1),
                'PRCP': round(prcp, 1),
                'WDSP': round(wdsp, 1)
            })
    
    df = pd.DataFrame(data)
    df.to_csv('dummy_weather_data.csv', index=False)
    print(f"Generated {len(df)} records for {len(cities)} cities")
    print(df.head())
    return df

if __name__ == "__main__":
    df = generate_dummy_weather_data()
