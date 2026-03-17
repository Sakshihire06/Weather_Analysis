# plot_original_weather.py
import pandas as pd
import matplotlib.pyplot as plt

def plot_original_data(input_file='dummy_weather_data.csv'):
    """
    Simple plot of original temperature data for all cities
    """
    
    # Load data
    df = pd.read_csv(input_file)
    df['DATE'] = pd.to_datetime(df['DATE'])
    
    # Create plot
    plt.figure(figsize=(12, 6))
    
    # Plot each city
    for city in df['CITY'].unique():
        city_data = df[df['CITY'] == city]
        plt.plot(city_data['DATE'], city_data['TEMP'], label=city, alpha=0.7, linewidth=1)
    
    plt.title('Original Temperature Data - All Cities', fontsize=14)
    plt.xlabel('Date')
    plt.ylabel('Temperature (°C)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    plot_original_data()
