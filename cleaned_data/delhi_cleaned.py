import numpy as np
import pandas as pd
from raw_data.delhi_raw import get_raw_data

MISSING_VALUES = {
    'TEMP': 9999.9, 'DEWP': 9999.9, 'SLP': 9999.9, 'STP': 9999.9,
    'VISIB': 999.9, 'WDSP': 999.9, 'MXSPD': 999.9, 'GUST': 999.9,
    'MAX': 9999.9, 'MIN': 9999.9, 'PRCP': 99.99, 'SNDP': 999.9,
}

IMD_HEAVY_RAIN   = 64.5
IMD_VERY_HEAVY   = 115.6
IMD_EXTREME_RAIN = 204.4
IMD_HEATWAVE     = 40.0
IMD_SEVERE_HEAT  = 45.0

KNOWN_EXTREMES = [
    (2002, 5, 'MAX', 'Delhi May 2002 heatwave - above 47C'),
    (2022, 5, 'MAX', 'Delhi May 2022 heatwave - 49.2C, hottest in 122 years'),
]


def clean(df):
    df = df.copy()

    # parse date, get year and month
    df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
    df = df.dropna(subset=['DATE']).copy()
    df['YEAR']  = df['DATE'].dt.year
    df['MONTH'] = df['DATE'].dt.month
    df = df.sort_values(['YEAR', 'MONTH', 'DATE']).reset_index(drop=True)

    # replace noaa missing value codes with nan
    for col, fill_val in MISSING_VALUES.items():
        if col in df.columns:
            df.loc[df[col] == fill_val, col] = np.nan

    # remove duplicate dates
    df = df.drop_duplicates(subset=['DATE'], keep='first')

    # convert imperial to metric
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

    # remove physically impossible values
    for col in ['PRCP', 'WDSP', 'MXSPD', 'GUST', 'SNDP', 'VISIB']:
        if col in df.columns:
            df.loc[df[col] < 0, col] = np.nan
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

    # flag extreme weather days (kept in data, just labelled)
    if 'PRCP' in df.columns:
        df['HEAVY_RAIN_DAY']      = df['PRCP'] >= IMD_HEAVY_RAIN
        df['VERY_HEAVY_RAIN_DAY'] = df['PRCP'] >= IMD_VERY_HEAVY
        df['EXTREME_RAIN_DAY']    = df['PRCP'] >= IMD_EXTREME_RAIN
    if 'MAX' in df.columns:
        df['HEATWAVE_DAY']    = df['MAX'] >= IMD_HEATWAVE
        df['SEVERE_HEAT_DAY'] = df['MAX'] >= IMD_SEVERE_HEAT

    # mark known historical events so they dont get removed by anomaly detection
    df['KNOWN_EXTREME']      = False
    df['KNOWN_EXTREME_DESC'] = ''
    for (ev_year, ev_month, ev_var, ev_desc) in KNOWN_EXTREMES:
        mask = (df['YEAR'] == ev_year) & (df['MONTH'] == ev_month)
        df.loc[mask, 'KNOWN_EXTREME']      = True
        df.loc[mask, 'KNOWN_EXTREME_DESC'] = ev_desc

    # robust anomaly scoring per month using median + mad
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
        df.loc[df['KNOWN_EXTREME'] == True, col + '_anomaly'] = False
        df[col + '_pctile'] = df.groupby('MONTH')[col].rank(pct=True).round(3)

    df = df.drop(columns=['DATE'], errors='ignore')
    print(f'Delhi cleaned - {len(df)} rows')
    return df


def get_cleaned_data():
    raw = get_raw_data()
    return clean(raw)


if __name__ == '__main__':
    df = get_cleaned_data()
    print(df.head())
