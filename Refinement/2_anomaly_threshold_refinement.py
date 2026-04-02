import numpy as np
import pandas as pd

from common import CITY_CONFIGS, CORE_NUMERIC_COLS, RESULTS_PATH, known_extreme_mask, load_city_cleaned_data, robust_zscore, save_table


THRESHOLDS = [2.5, 3.0, 3.5, 4.0, 4.5]


def evaluate_threshold(config, threshold):
    df = load_city_cleaned_data(config)
    df = df.sort_values("DATE").dropna(subset=["DATE"]).reset_index(drop=True)

    monitored_cols = [col for col in CORE_NUMERIC_COLS if col in df.columns]
    baseline_valid = int(df[monitored_cols].notna().sum().sum())
    anomaly_removed = 0

    for col in monitored_cols:
        zscore = robust_zscore(df[col], df["MONTH"])
        mask = zscore.abs() > threshold
        protected = known_extreme_mask(df, config)
        removed_here = int((mask & ~protected & df[col].notna()).sum())
        anomaly_removed += removed_here
        df.loc[mask & ~protected, col] = np.nan

    remaining_valid = int(df[monitored_cols].notna().sum().sum())
    residual_outliers = 0
    residual_total = 0

    for col in monitored_cols:
        residual_z = robust_zscore(df[col], df["MONTH"])
        residual_mask = df[col].notna()
        residual_total += int(residual_mask.sum())
        residual_outliers += int(((residual_z.abs() > 3.5) & residual_mask).sum())

    known_total = 0
    known_preserved = 0

    for col in monitored_cols:
        variable_mask = known_extreme_mask(df, config, variable=col)
        if variable_mask.any():
            known_total += int(variable_mask.sum())
            known_preserved += int(df.loc[variable_mask, col].notna().sum())

    if baseline_valid == 0:
        missing_pct = 0.0
    else:
        missing_pct = (1 - (remaining_valid / baseline_valid)) * 100

    if residual_total == 0:
        residual_outlier_pct = 0.0
    else:
        residual_outlier_pct = (residual_outliers / residual_total) * 100

    if known_total == 0:
        known_preservation_pct = 100.0
    else:
        known_preservation_pct = (known_preserved / known_total) * 100

    score = known_preservation_pct - (missing_pct * 1.6) - (residual_outlier_pct * 2.4)

    return {
        "City": config["name"],
        "Threshold": threshold,
        "Baseline Valid Values": baseline_valid,
        "Anomaly Values Removed": anomaly_removed,
        "Remaining Valid Values": remaining_valid,
        "Extra Missing After Threshold (%)": round(missing_pct, 2),
        "Residual Outliers (%)": round(residual_outlier_pct, 2),
        "Known Extreme Preservation (%)": round(known_preservation_pct, 2),
        "Composite Score": round(score, 2),
    }


def main():
    rows = []

    for config in CITY_CONFIGS:
        for threshold in THRESHOLDS:
            row = evaluate_threshold(config, threshold)
            rows.append(row)

    result_df = pd.DataFrame(rows)
    result_df = result_df.sort_values(["City", "Composite Score"], ascending=[True, False])
    best_df = result_df.groupby("City", as_index=False).first()

    save_table(result_df, "anomaly_threshold_refinement_all_results.csv")
    save_table(best_df, "anomaly_threshold_refinement_best_by_city.csv")
    print(f"Saved anomaly-threshold refinement outputs to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
