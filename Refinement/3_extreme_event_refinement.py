import os
import sys

import pandas as pd


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from common import CITY_CONFIGS, EXPECTED_HEAT_MONTHS, EXPECTED_RAIN_MONTHS, RESULTS_DIR, classify_extremes, load_all_cleaned_data, save_table


RULE_SETS = ["imd_fixed", "city_percentile", "season_aware_hybrid"]


def evaluate_rule(city_df, rule_name):
    flagged = classify_extremes(city_df, rule_name)

    total_days = len(flagged)
    heat_days = int(flagged["HEATWAVE_FLAG"].sum())
    heavy_rain_days = int(flagged["HEAVY_RAIN_FLAG"].sum())
    extreme_rain_days = int(flagged["EXTREME_RAIN_FLAG"].sum())

    heat_month_alignment = 0.0
    if heat_days:
        aligned = flagged.loc[flagged["HEATWAVE_FLAG"] == 1, "MONTH"].isin(EXPECTED_HEAT_MONTHS).mean()
        heat_month_alignment = aligned * 100

    rain_month_alignment = 0.0
    if heavy_rain_days:
        aligned = flagged.loc[flagged["HEAVY_RAIN_FLAG"] == 1, "MONTH"].isin(EXPECTED_RAIN_MONTHS).mean()
        rain_month_alignment = aligned * 100

    heat_non_event = flagged.loc[flagged["HEATWAVE_FLAG"] == 0, "MAX_C"]
    heat_event = flagged.loc[flagged["HEATWAVE_FLAG"] == 1, "MAX_C"]
    rain_non_event = flagged.loc[flagged["HEAVY_RAIN_FLAG"] == 0, "PRCP_MM"]
    rain_event = flagged.loc[flagged["HEAVY_RAIN_FLAG"] == 1, "PRCP_MM"]

    heat_separation = 0.0
    if len(heat_event) and len(heat_non_event):
        heat_separation = (heat_event.mean() - heat_non_event.mean()) / flagged["MAX_C"].std()

    rain_separation = 0.0
    if len(rain_event) and len(rain_non_event):
        rain_separation = (rain_event.mean() - rain_non_event.mean()) / max(flagged["PRCP_MM"].std(), 1e-9)

    if total_days == 0:
        event_rate_pct = 0.0
    else:
        event_rate_pct = ((heat_days + heavy_rain_days) / (2 * total_days)) * 100

    score = 0
    score += heat_month_alignment * 0.25
    score += rain_month_alignment * 0.25
    score += heat_separation * 20
    score += rain_separation * 10
    score -= abs(event_rate_pct - 5.0) * 2

    return {
        "City": str(city_df["CITY"].dropna().iloc[0]),
        "Rule Set": rule_name,
        "Heatwave Days": heat_days,
        "Heavy Rain Days": heavy_rain_days,
        "Extreme Rain Days": extreme_rain_days,
        "Heat Month Alignment (%)": round(heat_month_alignment, 2),
        "Rain Month Alignment (%)": round(rain_month_alignment, 2),
        "Heat Intensity Separation": round(heat_separation, 3),
        "Rain Intensity Separation": round(rain_separation, 3),
        "Combined Event Rate (%)": round(event_rate_pct, 2),
        "Composite Score": round(score, 2),
    }


def main():
    all_data = load_all_cleaned_data()
    all_data["DATE"] = pd.to_datetime(all_data["DATE"], errors="coerce")
    rows = []

    for config in CITY_CONFIGS:
        city_df = all_data[all_data["CITY"] == config["name"]].copy()
        city_df = city_df.sort_values("DATE")
        for rule_name in RULE_SETS:
            row = evaluate_rule(city_df, rule_name)
            rows.append(row)

    result_df = pd.DataFrame(rows)
    result_df = result_df.sort_values(["City", "Composite Score"], ascending=[True, False])
    best_df = result_df.groupby("City", as_index=False).first()

    save_table(result_df, "extreme_event_refinement_all_results.csv")
    save_table(best_df, "extreme_event_refinement_best_by_city.csv")
    print(f"Saved extreme-event refinement outputs to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
