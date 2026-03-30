"""Import guide:

Use direct package imports such as:
    from visualization import run_eda_pipeline
    from visualization import plot_yearly_trend, create_monthly_df
"""

from .trend_analysis import (
    CITY_COLORS,
    add_rolling,
    create_monthly_df,
    create_variability_df,
    create_yearly_df,
    load_all_saved_cleaned_data,
    plot_all_heatmaps,
    plot_extreme_events,
    plot_precip_cycle,
    plot_rain_extremes,
    plot_seasonal_cycle,
    plot_variability,
    plot_yearly_trend,
    prepare_analysis_df,
    run_eda_pipeline,
)
