import math
import os
import sys

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from common import CITY_CONFIGS, RESULTS_DIR, load_all_cleaned_data, save_table, safe_ratio


ROLLING_WINDOWS = [7, 15, 30, 45, 60, 90]
STL_PERIODS = [90,180,365]
HARMONIC_COUNTS = [2, 4, 6, 8]


def rolling_smooth(series, window):
    return series.rolling(window=window, center=True, min_periods=max(3, window // 3)).mean()


def stl_smooth(series, period):
    stl = STL(series, period=period, robust=True)
    result = stl.fit()
    return pd.Series(result.trend + result.seasonal, index=series.index)


def harmonic_smooth(series, harmonics):
    values = series.to_numpy(dtype=float)
    n = len(values)
    fft_vals = np.fft.fft(values)
    keep = np.zeros(n, dtype=bool)
    keep[0] = True

    positive_indices = np.arange(1, max(1, n // 2))
    order = positive_indices[np.argsort(np.abs(fft_vals[positive_indices]))[::-1]]
    selected = order[:harmonics]

    keep[selected] = True
    keep[-selected] = True

    filtered = np.where(keep, fft_vals, 0)
    reconstructed = np.fft.ifft(filtered).real
    return pd.Series(reconstructed, index=series.index)


def evaluate_candidate(original, smoothed, city, method, parameter):
    frame = pd.DataFrame({"original": original, "smoothed": smoothed}).dropna()

    if len(frame) < 30:
        return {
            "City": city,
            "Method": method,
            "Parameter": parameter,
            "Points Used": len(frame),
            "Noise Reduction (%)": np.nan,
            "RMSE Ratio": np.nan,
            "Roughness Ratio": np.nan,
            "Composite Score": np.nan,
        }

    original_std = frame["original"].std()
    smooth_std = frame["smoothed"].std()
    diff_original = frame["original"].diff().dropna().std()
    diff_smoothed = frame["smoothed"].diff().dropna().std()
    rmse = math.sqrt(np.mean((frame["original"] - frame["smoothed"]) ** 2))

    noise_reduction = (1 - safe_ratio(smooth_std, original_std)) * 100
    rmse_ratio = safe_ratio(rmse, original_std)
    roughness_ratio = safe_ratio(diff_smoothed, diff_original)
    score = noise_reduction - (rmse_ratio * 35) - (roughness_ratio * 20)

    return {
        "City": city,
        "Method": method,
        "Parameter": parameter,
        "Points Used": len(frame),
        "Noise Reduction (%)": round(noise_reduction, 2),
        "RMSE Ratio": round(rmse_ratio, 4),
        "Roughness Ratio": round(roughness_ratio, 4),
        "Composite Score": round(score, 2),
    }


def build_candidates(series):
    candidates = []

    for window in ROLLING_WINDOWS:
        candidates.append(("Rolling", f"window={window}", rolling_smooth(series, window)))

    for period in STL_PERIODS:
        candidates.append(("STL", f"period={period}", stl_smooth(series, period)))

    for harmonics in HARMONIC_COUNTS:
        candidates.append(("Harmonic", f"harmonics={harmonics}", harmonic_smooth(series, harmonics)))

    return candidates


def main():
    all_data = load_all_cleaned_data()
    results = []

    for config in CITY_CONFIGS:
        city_df = all_data[all_data["CITY"] == config["name"]].copy()
        city_df = city_df.sort_values("DATE")
        city_df["DATE"] = pd.to_datetime(city_df["DATE"], errors="coerce")
        city_df = city_df.dropna(subset=["DATE"])
        city_df = city_df.set_index("DATE").asfreq("D")
        series = city_df["TEMP_C"].interpolate(limit_direction="both").dropna()

        candidates = build_candidates(series)
        for method, parameter, smoothed in candidates:
            row = evaluate_candidate(series, smoothed, config["name"], method, parameter)
            results.append(row)

    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values(["City", "Composite Score"], ascending=[True, False])
    best_df = result_df.dropna(subset=["Composite Score"]).groupby("City", as_index=False).first()

    save_table(result_df, "smoothing_refinement_all_results.csv")
    save_table(best_df, "smoothing_refinement_best_by_city.csv")
    print(f"Saved smoothing refinement outputs to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
