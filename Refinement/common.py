import os
import sys

import numpy as np
import pandas as pd


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
if PROJECT_DIR not in sys.path:
    sys.path.append(PROJECT_DIR)

import cleaned_data.dehradun_cleaned as dehradun_cleaned_module
import cleaned_data.delhi_cleaned as delhi_cleaned_module
import cleaned_data.jodhpur_cleaned as jodhpur_cleaned_module
import cleaned_data.mumbai_cleaned as mumbai_cleaned_module
from raw_data.dehradun_raw import get_raw_data as get_dehradun_raw
from raw_data.delhi_raw import get_raw_data as get_delhi_raw
from raw_data.jodhpur_raw import get_raw_data as get_jodhpur_raw
from raw_data.mumbai_raw import get_raw_data as get_mumbai_raw

RESULTS_DIR = os.path.join(CURRENT_DIR, "results")
CLEANED_DATA_DIR = os.path.join(PROJECT_DIR, "cleaned_data", "nc_cleaned")

CORE_NUMERIC_COLS = ["TEMP_C", "MAX_C", "MIN_C", "DEWP_C", "PRCP_MM", "WDSP_MS"]
EXPECTED_HEAT_MONTHS = {3, 4, 5, 6}
EXPECTED_RAIN_MONTHS = {6, 7, 8, 9}

CITY_CONFIGS = [
    {"name": "Mumbai", "filename": "mumbai_cleaned.nc", "clean_module": mumbai_cleaned_module, "raw_loader": get_mumbai_raw},
    {"name": "Delhi", "filename": "delhi_cleaned.nc", "clean_module": delhi_cleaned_module, "raw_loader": get_delhi_raw},
    {"name": "Dehradun", "filename": "dehradun_cleaned.nc", "clean_module": dehradun_cleaned_module, "raw_loader": get_dehradun_raw},
    {"name": "Jodhpur", "filename": "jodhpur_cleaned.nc", "clean_module": jodhpur_cleaned_module, "raw_loader": get_jodhpur_raw},
]


def save_table(df, filename):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    output_path = os.path.join(RESULTS_DIR, filename)
    df.to_csv(output_path, index=False)
    return output_path


def normalize_refinement_schema(df, city_name):
    df = df.copy()
    rename_map = {
        "TEMP": "TEMP_C",
        "DEWP": "DEWP_C",
        "PRCP": "PRCP_MM",
        "WDSP": "WDSP_MS",
        "MXSPD": "MXSPD_MS",
        "GUST": "GUST_MS",
        "MAX": "MAX_C",
        "MIN": "MIN_C",
    }
    existing_renames = {old: new for old, new in rename_map.items() if old in df.columns}
    if existing_renames:
        df = df.rename(columns=existing_renames)

    if "CITY" not in df.columns:
        df["CITY"] = city_name
    else:
        df["CITY"] = df["CITY"].fillna(city_name)

    if "DATE" in df.columns:
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

    if "YEAR" not in df.columns and "DATE" in df.columns:
        df["YEAR"] = df["DATE"].dt.year

    if "MONTH" not in df.columns and "DATE" in df.columns:
        df["MONTH"] = df["DATE"].dt.month

    return df


def load_saved_cleaned_city(filename, city_name):
    path = os.path.join(CLEANED_DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Saved cleaned file not found: {path}")

    try:
        import xarray as xr
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "xarray is required to load saved .nc cleaned files. Install it with: pip install xarray"
        ) from exc

    with xr.open_dataset(path) as ds:
        df = ds.to_dataframe().reset_index()

    return normalize_refinement_schema(df, city_name)


def load_city_cleaned_data(config):
    df = load_saved_cleaned_city(config["filename"], config["name"])

    if "DATE" not in df.columns:
        raw_df = config["raw_loader"]()
        if "DATE" in raw_df.columns and len(raw_df) == len(df):
            df["DATE"] = pd.to_datetime(raw_df["DATE"], errors="coerce")
        else:
            raise ValueError(
                f"Could not align DATE metadata for {config['name']} from saved cleaned data and raw data."
            )

        if "YEAR" not in df.columns:
            df["YEAR"] = df["DATE"].dt.year
        if "MONTH" not in df.columns:
            df["MONTH"] = df["DATE"].dt.month

    return df


def load_all_cleaned_data():
    frames = []
    for config in CITY_CONFIGS:
        city_df = load_city_cleaned_data(config)
        frames.append(city_df)
    return pd.concat(frames, ignore_index=True)


def known_extreme_mask(df, config, variable=None):
    known_extremes = getattr(config["clean_module"], "KNOWN_EXTREMES", [])
    mask = pd.Series(False, index=df.index)

    for year, month, event_var, _ in known_extremes:
        if variable is not None:
            short_name = variable.replace("_MM", "").replace("_C", "")
            if event_var not in [variable, short_name]:
                continue
        mask = mask | ((df["YEAR"] == year) & (df["MONTH"] == month))

    return mask


def robust_zscore(series, group_labels):
    monthly_median = series.groupby(group_labels).transform("median")
    monthly_mad = series.groupby(group_labels).transform(lambda x: (x - x.median()).abs().median())
    zscore = np.where(monthly_mad > 0, 0.6745 * (series - monthly_median) / monthly_mad, 0.0)
    return pd.Series(zscore, index=series.index)


def classify_extremes(df, rule_name):
    df = df.copy()

    if "MAX_C" in df.columns:
        heat_series = df["MAX_C"]
    else:
        heat_series = df["TEMP_C"]

    rain_series = df["PRCP_MM"]

    if rule_name == "imd_fixed":
        df["HEATWAVE_FLAG"] = (heat_series >= 40.0).astype(int)
        df["HEAVY_RAIN_FLAG"] = (rain_series >= 64.5).astype(int)
        df["EXTREME_RAIN_FLAG"] = (rain_series >= 204.4).astype(int)
        return df

    if rule_name == "city_percentile":
        heat_threshold = heat_series.quantile(0.95)
        heavy_rain_threshold = rain_series.quantile(0.95)
        extreme_rain_threshold = rain_series.quantile(0.99)
        df["HEATWAVE_FLAG"] = (heat_series >= heat_threshold).astype(int)
        df["HEAVY_RAIN_FLAG"] = (rain_series >= heavy_rain_threshold).astype(int)
        df["EXTREME_RAIN_FLAG"] = (rain_series >= extreme_rain_threshold).astype(int)
        return df

    if rule_name == "season_aware_hybrid":
        heat_reference = heat_series[df["MONTH"].isin(EXPECTED_HEAT_MONTHS)]
        rain_reference = rain_series[df["MONTH"].isin(EXPECTED_RAIN_MONTHS)]

        if heat_reference.empty:
            heat_threshold = 40.0
        else:
            heat_threshold = max(40.0, float(heat_reference.quantile(0.90)))

        if rain_reference.empty:
            heavy_rain_threshold = 64.5
            extreme_rain_threshold = 204.4
        else:
            heavy_rain_threshold = max(64.5, float(rain_reference.quantile(0.90)))
            extreme_rain_threshold = max(204.4, float(rain_reference.quantile(0.98)))

        df["HEATWAVE_FLAG"] = ((heat_series >= heat_threshold) & df["MONTH"].isin(EXPECTED_HEAT_MONTHS)).astype(int)
        df["HEAVY_RAIN_FLAG"] = ((rain_series >= heavy_rain_threshold) & df["MONTH"].isin(EXPECTED_RAIN_MONTHS)).astype(int)
        df["EXTREME_RAIN_FLAG"] = ((rain_series >= extreme_rain_threshold) & df["MONTH"].isin(EXPECTED_RAIN_MONTHS)).astype(int)
        return df

    raise ValueError("Unsupported rule set")


def safe_ratio(numerator, denominator):
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return float(numerator) / float(denominator)
