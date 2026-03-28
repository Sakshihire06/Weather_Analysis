import numpy as np
import pandas as pd
from raw_data.dehradun_raw import get_raw_data

# noaa fill values - these are not real values, just mean data is missing
MISSING_VALUES = {
    'TEMP': 9999.9,
    'DEWP': 9999.9,
    'SLP':  9999.9,
    'STP':  9999.9,
    'VISIB': 999.9,
    'WDSP':  999.9,
    'MXSPD': 999.9,
    'GUST':  999.9,
    'MAX':  9999.9,
    'MIN':  9999.9,
    'PRCP':  99.99,
    'SNDP':  999.9,
}

# imd thresholds for flagging extreme weather
IMD_HEAVY_RAIN   = 64.5
IMD_VERY_HEAVY   = 115.6
IMD_EXTREME_RAIN = 204.4
IMD_HEATWAVE     = 40.0
IMD_SEVERE_HEAT  = 45.0

# known historical events for dehradun - these should never be removed
KNOWN_EXTREMES = [
    (2013, 6, 'PRCP', 'Uttarakhand Jun 2013 cloudbursts - 5000+ deaths, Kedarnath disaster'),
]


def clean(df):
    df = df.copy()
    city_name = 'Dehradun'

    # parse date and pull out year/month
    df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
    df = df.dropna(subset=['DATE']).copy()
    df['YEAR']  = df['DATE'].dt.year
    df['MONTH'] = df['DATE'].dt.month
    df['SEASON'] = df['MONTH'].map({
        12: 'Winter',   1: 'Winter',   2: 'Winter',
        3: 'Pre-Monsoon', 4: 'Pre-Monsoon', 5: 'Pre-Monsoon',
        6: 'Monsoon',   7: 'Monsoon',  8: 'Monsoon',
        9: 'Post-Monsoon', 10: 'Post-Monsoon', 11: 'Post-Monsoon'
    })
    df = df.sort_values(['YEAR', 'MONTH', 'DATE']).reset_index(drop=True)

    # replace noaa sentinel values with nan
    for col, fill_val in MISSING_VALUES.items():
        if col in df.columns:
            df.loc[df[col] == fill_val, col] = np.nan

    # remove duplicate dates, keep first
    df = df.drop_duplicates(subset=['DATE'], keep='first')

    # unit conversion - noaa gives imperial, we want metric
    for col in ['TEMP', 'DEWP', 'MAX', 'MIN']:
        if col in df.columns:
            df[col] = (df[col] - 32) * 5 / 9
    for col in ['PRCP', 'SNDP']:
        if col in df.columns:
            df[col] = df[col] * 25.4
    for col in ['WDSP', 'MXSPD', 'GUST']:
        if col in df.columns:
            df[col] = df[col] * 0.514444
    if 'VISIB' in df.columns:
        df['VISIB'] = df['VISIB'] * 1.60934

    # remove impossible negative values
    for col in ['PRCP', 'WDSP', 'MXSPD', 'GUST', 'SNDP', 'VISIB']:
        if col in df.columns:
            df.loc[df[col] < 0, col] = np.nan

    # remove physically impossible values (earth record limits)
    for col in ['TEMP', 'MAX', 'MIN', 'DEWP']:
        if col in df.columns:
            df.loc[(df[col] < -90) | (df[col] > 60), col] = np.nan
    if 'PRCP' in df.columns:
        df.loc[df['PRCP'] > 2000, 'PRCP'] = np.nan
    if 'WDSP' in df.columns:
        df.loc[df['WDSP'] > 90, 'WDSP'] = np.nan
    if 'MAX' in df.columns and 'MIN' in df.columns:
        df.loc[df['MAX'] < df['MIN'], ['MAX', 'MIN']] = np.nan
    if 'DEWP' in df.columns and 'TEMP' in df.columns:
        df.loc[df['DEWP'] > (df['TEMP'] + 2), 'DEWP'] = np.nan

    # flag heavy rain and heatwave days (kept in data, just labelled)
    if 'PRCP' in df.columns:
        df['HEAVY_RAIN_DAY']      = df['PRCP'] >= IMD_HEAVY_RAIN
        df['VERY_HEAVY_RAIN_DAY'] = df['PRCP'] >= IMD_VERY_HEAVY
        df['EXTREME_RAIN_DAY']    = df['PRCP'] >= IMD_EXTREME_RAIN
    if 'MAX' in df.columns:
        df['HEATWAVE_DAY']    = df['MAX'] >= IMD_HEATWAVE
        df['SEVERE_HEAT_DAY'] = df['MAX'] >= IMD_SEVERE_HEAT

    # mark known historical events so they dont get flagged as errors
    df['KNOWN_EXTREME']      = False
    df['KNOWN_EXTREME_DESC'] = ''
    for (ev_year, ev_month, ev_var, ev_desc) in KNOWN_EXTREMES:
        mask = (df['YEAR'] == ev_year) & (df['MONTH'] == ev_month)
        df.loc[mask, 'KNOWN_EXTREME']      = True
        df.loc[mask, 'KNOWN_EXTREME_DESC'] = ev_desc

    # anomaly scoring using median + mad (more robust than mean + std for weather data)
    for col in ['TEMP', 'MAX', 'MIN', 'PRCP', 'WDSP', 'DEWP']:
        if col not in df.columns:
            continue
        monthly_median = df.groupby('MONTH')[col].transform('median')
        monthly_mad    = df.groupby('MONTH')[col].transform(
            lambda x: (x - x.median()).abs().median()
        )
        df[col + '_zscore']  = np.where(
            monthly_mad > 0,
            0.6745 * (df[col] - monthly_median) / monthly_mad,
            0.0
        )
        df[col + '_anomaly'] = df[col + '_zscore'].abs() > 3.5
        # dont flag known events as anomalies
        df.loc[df['KNOWN_EXTREME'] == True, col + '_anomaly'] = False
        df[col + '_pctile'] = df.groupby('MONTH')[col].rank(pct=True).round(3)

    df = df.drop(columns=['DATE'], errors='ignore')
    print(f'{city_name} cleaned - {len(df)} rows')
    return df


def get_cleaned_data():
    raw = get_raw_data()
    return clean(raw)


if __name__ == '__main__':
    df = get_cleaned_data()
    print(df.head())
