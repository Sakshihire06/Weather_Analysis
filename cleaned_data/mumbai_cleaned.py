import numpy as np
import pandas as pd
from raw_data.mumbai_raw import get_raw_data

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
    (2005, 7, 'PRCP', 'Mumbai 26 Jul 2005 floods - ~944mm in one day'),
    (2017, 8, 'PRCP', 'Mumbai Aug 2017 monsoon floods'),
]

REQUIRED_COLUMNS = [
    'YEAR', 'MONTH',
    'TEMP_C', 'MAX_C', 'MIN_C',
    'DEWP_C', 'PRCP_MM',
    'WDSP_MS', 'MXSPD_MS', 'GUST_MS',
    'FRSHTT',
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

    # rename columns to reflect metric units
    df = df.rename(columns={
        'TEMP':  'TEMP_C',
        'MAX':   'MAX_C',
        'MIN':   'MIN_C',
        'DEWP':  'DEWP_C',
        'PRCP':  'PRCP_MM',
        'WDSP':  'WDSP_MS',
        'MXSPD': 'MXSPD_MS',
        'GUST':  'GUST_MS',
    })

    # remove physically impossible values
    for col in ['PRCP_MM', 'WDSP_MS', 'MXSPD_MS', 'GUST_MS']:
        if col in df.columns:
            df.loc[df[col] < 0, col] = np.nan
    for col in ['TEMP_C', 'MAX_C', 'MIN_C', 'DEWP_C']:
        if col in df.columns:
            df.loc[(df[col] < -90) | (df[col] > 60), col] = np.nan
    if 'PRCP_MM' in df.columns:
        df.loc[df['PRCP_MM'] > 2000, 'PRCP_MM'] = np.nan
    if 'WDSP_MS' in df.columns:
        df.loc[df['WDSP_MS'] > 90, 'WDSP_MS'] = np.nan
    if 'MAX_C' in df.columns and 'MIN_C' in df.columns:
        df.loc[df['MAX_C'] < df['MIN_C'], ['MAX_C', 'MIN_C']] = np.nan
    if 'DEWP_C' in df.columns and 'TEMP_C' in df.columns:
        df.loc[df['DEWP_C'] > (df['TEMP_C'] + 2), 'DEWP_C'] = np.nan

    # anomaly detection (internal only - used to guard known extremes, not exported)
    df['_KNOWN_EXTREME'] = False
    for (ev_year, ev_month, ev_var, ev_desc) in KNOWN_EXTREMES:
        mask = (df['YEAR'] == ev_year) & (df['MONTH'] == ev_month)
        df.loc[mask, '_KNOWN_EXTREME'] = True

    for col in ['TEMP_C', 'MAX_C', 'MIN_C', 'PRCP_MM', 'WDSP_MS', 'DEWP_C']:
        if col not in df.columns:
            continue
        monthly_median = df.groupby('MONTH')[col].transform('median')
        monthly_mad    = df.groupby('MONTH')[col].transform(
            lambda x: (x - x.median()).abs().median()
        )
        zscore = np.where(
            monthly_mad > 0,
            0.6745 * (df[col] - monthly_median) / monthly_mad,
            0.0
        )
        is_anomaly = pd.Series(np.abs(zscore) > 3.5, index=df.index)
        # null out anomalies that are NOT known extremes
        df.loc[is_anomaly & ~df['_KNOWN_EXTREME'], col] = np.nan

    # keep only required columns (drop internal helpers and everything else)
    output_cols = [c for c in REQUIRED_COLUMNS if c in df.columns]
    df = df[output_cols]

    print(f'Mumbai cleaned - {len(df)} rows, {len(df.columns)} columns')
    return df


def get_cleaned_data():
    raw = get_raw_data()
    return clean(raw)


if __name__ == '__main__':
    df = get_cleaned_data()
    print(df.head())
