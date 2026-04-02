import os
import sys

from dash import Dash, Input, Output, dash_table, dcc, html
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from cleaned_data.dehradun_cleaned import get_cleaned_data as get_dehradun_data
from cleaned_data.delhi_cleaned import get_cleaned_data as get_delhi_data
from cleaned_data.jodhpur_cleaned import get_cleaned_data as get_jodhpur_data
from cleaned_data.mumbai_cleaned import get_cleaned_data as get_mumbai_data


REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
REFINEMENT_RESULTS_DIR = os.path.join(PROJECT_ROOT, "Refinement", "results")
TREND_RESULTS_DIR = os.path.join(PROJECT_ROOT, "Trend_analysis", "results")

CITY_COLORS = {
    "Mumbai": "#0081a7",
    "Delhi": "#f4a261",
    "Dehradun": "#2a9d8f",
    "Jodhpur": "#c1121f",
}
HEAT_MONTHS = {3, 4, 5, 6}
RAIN_MONTHS = {6, 7, 8, 9}


def safe_read_csv(*parts):
    path = os.path.join(*parts)
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


def load_cleaned_data():
    city_loaders = [
        ("Mumbai", get_mumbai_data),
        ("Delhi", get_delhi_data),
        ("Dehradun", get_dehradun_data),
        ("Jodhpur", get_jodhpur_data),
    ]
    frames = []

    for city, loader in city_loaders:
        city_df = loader().copy()
        city_df["CITY"] = city
        city_df["DATE"] = pd.to_datetime(city_df["DATE"], errors="coerce")
        if "YEAR" not in city_df.columns:
            city_df["YEAR"] = city_df["DATE"].dt.year
        if "MONTH" not in city_df.columns:
            city_df["MONTH"] = city_df["DATE"].dt.month
        frames.append(city_df)

    return pd.concat(frames, ignore_index=True)


def compute_extreme_flags(city_df, rule_name):
    flagged = city_df.copy()
    heat_series = flagged["MAX_C"] if "MAX_C" in flagged.columns else flagged["TEMP_C"]
    rain_series = flagged["PRCP_MM"]

    if rule_name == "imd_fixed":
        flagged["HEATWAVE_DAY"] = (heat_series >= 40.0).astype(int)
        flagged["HEAVY_RAIN_DAY"] = (rain_series >= 64.5).astype(int)
        flagged["EXTREME_RAIN_DAY"] = (rain_series >= 204.4).astype(int)
        return flagged

    if rule_name == "city_percentile":
        flagged["HEATWAVE_DAY"] = (heat_series >= heat_series.quantile(0.95)).astype(int)
        flagged["HEAVY_RAIN_DAY"] = (rain_series >= rain_series.quantile(0.95)).astype(int)
        flagged["EXTREME_RAIN_DAY"] = (rain_series >= rain_series.quantile(0.99)).astype(int)
        return flagged

    heat_reference = heat_series[flagged["MONTH"].isin(HEAT_MONTHS)]
    rain_reference = rain_series[flagged["MONTH"].isin(RAIN_MONTHS)]
    heat_threshold = max(40.0, float(heat_reference.quantile(0.90))) if not heat_reference.empty else 40.0
    heavy_rain_threshold = max(64.5, float(rain_reference.quantile(0.90))) if not rain_reference.empty else 64.5
    extreme_rain_threshold = max(204.4, float(rain_reference.quantile(0.98))) if not rain_reference.empty else 204.4

    flagged["HEATWAVE_DAY"] = ((heat_series >= heat_threshold) & flagged["MONTH"].isin(HEAT_MONTHS)).astype(int)
    flagged["HEAVY_RAIN_DAY"] = ((rain_series >= heavy_rain_threshold) & flagged["MONTH"].isin(RAIN_MONTHS)).astype(int)
    flagged["EXTREME_RAIN_DAY"] = ((rain_series >= extreme_rain_threshold) & flagged["MONTH"].isin(RAIN_MONTHS)).astype(int)
    return flagged


def build_daily_analysis(raw_df, extreme_rules):
    frames = []
    default_rule = "season_aware_hybrid"

    for city in sorted(raw_df["CITY"].dropna().unique()):
        city_df = raw_df[raw_df["CITY"] == city].copy()
        rule_name = extreme_rules.get(city, default_rule)
        frames.append(compute_extreme_flags(city_df, rule_name))

    return pd.concat(frames, ignore_index=True)


def build_refinement_summary(smoothing_df, anomaly_df, extreme_df):
    smooth = smoothing_df.rename(
        columns={
            "Method": "Best Smoothing",
            "Parameter": "Best Smoothing Parameter",
            "Composite Score": "Smoothing Score",
        }
    )
    anomaly = anomaly_df.rename(
        columns={
            "Threshold": "Best Anomaly Threshold",
            "Composite Score": "Anomaly Score",
        }
    )
    extreme = extreme_df.rename(
        columns={
            "Rule Set": "Best Extreme Rule",
            "Composite Score": "Extreme Score",
        }
    )

    summary = smooth.merge(anomaly, on="City", how="outer").merge(extreme, on="City", how="outer")
    ordered_cols = [
        "City",
        "Best Smoothing",
        "Best Smoothing Parameter",
        "Noise Reduction (%)",
        "Best Anomaly Threshold",
        "Residual Outliers (%)",
        "Best Extreme Rule",
        "Heatwave Days",
        "Heavy Rain Days",
        "Extreme Rain Days",
        "Smoothing Score",
        "Anomaly Score",
        "Extreme Score",
    ]
    existing_cols = [col for col in ordered_cols if col in summary.columns]
    return summary[existing_cols].sort_values("City").reset_index(drop=True)


def load_dashboard_data():
    raw_df = load_cleaned_data()
    monthly_df = safe_read_csv(REPORTS_DIR, "monthly_summary.csv")
    yearly_df = safe_read_csv(REPORTS_DIR, "yearly_summary.csv")
    variability_df = safe_read_csv(REPORTS_DIR, "yearly_variability.csv")
    smoothing_df = safe_read_csv(REFINEMENT_RESULTS_DIR, "smoothing_refinement_best_by_city.csv")
    anomaly_df = safe_read_csv(REFINEMENT_RESULTS_DIR, "anomaly_threshold_refinement_best_by_city.csv")
    extreme_df = safe_read_csv(REFINEMENT_RESULTS_DIR, "extreme_event_refinement_best_by_city.csv")
    trend_comparison_df = safe_read_csv(TREND_RESULTS_DIR, "method_comparison.csv")

    extreme_rule_map = {}
    if not extreme_df.empty:
        extreme_rule_map = dict(zip(extreme_df["City"], extreme_df["Rule Set"]))

    analysis_df = build_daily_analysis(raw_df, extreme_rule_map)
    refinement_summary_df = build_refinement_summary(smoothing_df, anomaly_df, extreme_df)

    return {
        "analysis": analysis_df,
        "monthly": monthly_df,
        "yearly": yearly_df,
        "variability": variability_df,
        "smoothing": smoothing_df,
        "anomaly": anomaly_df,
        "extreme": extreme_df,
        "trend_comparison": trend_comparison_df,
        "refinement_summary": refinement_summary_df,
    }


DATA = load_dashboard_data()
analysis_df = DATA["analysis"]
monthly_df = DATA["monthly"]
yearly_df = DATA["yearly"]
variability_df = DATA["variability"]
smoothing_df = DATA["smoothing"]
extreme_df = DATA["extreme"]
refinement_summary_df = DATA["refinement_summary"]
available_cities = sorted(analysis_df["CITY"].dropna().unique().tolist())

PANEL_STYLE = {
    "backgroundColor": "rgba(250, 248, 244, 0.88)",
    "border": "1px solid rgba(27, 44, 58, 0.10)",
    "borderRadius": "24px",
    "boxShadow": "0 20px 48px rgba(28, 38, 45, 0.08)",
}

CARD_BASE_STYLE = {
    "padding": "24px",
    "borderRadius": "22px",
    "boxShadow": "0 18px 36px rgba(28, 36, 39, 0.08)",
    "border": "1px solid rgba(255,255,255,0.55)",
    "color": "#13212b",
}

GRAPH_STYLE = {**PANEL_STYLE, "padding": "12px"}
TAB_STYLE = {
    "padding": "12px 16px",
    "border": "none",
    "backgroundColor": "transparent",
    "color": "#51606b",
    "fontWeight": "bold",
}
TAB_SELECTED_STYLE = {
    "padding": "12px 16px",
    "border": "none",
    "borderBottom": "3px solid #31586a",
    "backgroundColor": "transparent",
    "color": "#1d2a34",
    "fontWeight": "bold",
}


def section_heading(eyebrow, title, subtitle):
    return html.Div(
        style={"marginBottom": "14px"},
        children=[
            html.Div(
                eyebrow,
                style={
                    "fontSize": "11px",
                    "letterSpacing": "1.6px",
                    "textTransform": "uppercase",
                    "fontWeight": "bold",
                    "color": "#4e6676",
                    "marginBottom": "8px",
                },
            ),
            html.H2(
                title,
                style={
                    "margin": "0 0 8px 0",
                    "fontSize": "30px",
                    "lineHeight": "1.08",
                    "color": "#1d2a34",
                },
            ),
            html.P(
                subtitle,
                style={
                    "margin": "0",
                    "fontSize": "14px",
                    "lineHeight": "1.6",
                    "color": "#5f6871",
                    "maxWidth": "780px",
                },
            ),
        ],
    )


def panel_header(eyebrow, title, subtitle=None):
    children = [
        html.Div(
            eyebrow,
            style={
                "fontSize": "10px",
                "fontWeight": "bold",
                "letterSpacing": "1.4px",
                "textTransform": "uppercase",
                "color": "#61798b",
                "marginBottom": "6px",
            },
        ),
        html.H3(
            title,
            style={
                "margin": "0",
                "fontSize": "22px",
                "lineHeight": "1.15",
                "color": "#1d2a34",
            },
        ),
    ]
    if subtitle:
        children.append(
            html.P(
                subtitle,
                style={
                    "margin": "8px 0 0 0",
                    "fontSize": "13px",
                    "lineHeight": "1.55",
                    "color": "#61707d",
                },
            )
        )
    return html.Div(style={"marginBottom": "12px"}, children=children)


def build_city_snapshot_cards(selected_cities, filtered_analysis, filtered_summary):
    cards = []

    for city in selected_cities:
        city_df = filtered_analysis[filtered_analysis["CITY"] == city].copy()
        city_summary = filtered_summary[filtered_summary["City"] == city].copy() if not filtered_summary.empty else pd.DataFrame()

        avg_temp = city_df["TEMP_C"].mean() if not city_df.empty else float("nan")
        avg_rain = city_df["PRCP_MM"].mean() if not city_df.empty else float("nan")
        heatwave_days = int(city_df["HEATWAVE_DAY"].fillna(0).sum()) if not city_df.empty else 0
        heavy_rain_days = int(city_df["HEAVY_RAIN_DAY"].fillna(0).sum()) if not city_df.empty else 0

        smoothing_method = "Not available"
        anomaly_threshold = "Not available"
        extreme_rule = "Not available"
        if not city_summary.empty:
            row = city_summary.iloc[0]
            smoothing_method = f"{row.get('Best Smoothing', 'N/A')} ({row.get('Best Smoothing Parameter', 'N/A')})"
            anomaly_threshold = str(row.get("Best Anomaly Threshold", "N/A"))
            extreme_rule = str(row.get("Best Extreme Rule", "N/A"))

        cards.append(
            html.Div(
                style={
                    **CARD_BASE_STYLE,
                    "background": "linear-gradient(180deg, rgba(255,255,255,0.88), rgba(242,238,231,0.92))",
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "12px",
                },
                children=[
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                        children=[
                            html.H3(city, style={"margin": "0", "fontSize": "24px", "color": "#1d2a34"}),
                            html.Div(
                                style={
                                    "width": "14px",
                                    "height": "14px",
                                    "borderRadius": "999px",
                                    "backgroundColor": CITY_COLORS.get(city, "#31586a"),
                                }
                            ),
                        ],
                    ),
                    html.Div(
                        style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"},
                        children=[
                            html.Div(
                                [
                                    html.Div("Average temperature", style={"fontSize": "12px", "color": "#6a7680", "marginBottom": "4px"}),
                                    html.Div(f"{avg_temp:.2f} C", style={"fontSize": "24px", "fontWeight": "bold"}),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Div("Average rainfall", style={"fontSize": "12px", "color": "#6a7680", "marginBottom": "4px"}),
                                    html.Div(f"{avg_rain:.2f} mm", style={"fontSize": "24px", "fontWeight": "bold"}),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Div("Heatwave days", style={"fontSize": "12px", "color": "#6a7680", "marginBottom": "4px"}),
                                    html.Div(f"{heatwave_days:,}", style={"fontSize": "22px", "fontWeight": "bold"}),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Div("Heavy-rain days", style={"fontSize": "12px", "color": "#6a7680", "marginBottom": "4px"}),
                                    html.Div(f"{heavy_rain_days:,}", style={"fontSize": "22px", "fontWeight": "bold"}),
                                ]
                            ),
                        ],
                    ),
                    html.Div(
                        style={
                            "padding": "14px 16px",
                            "borderRadius": "16px",
                            "backgroundColor": "rgba(49, 88, 106, 0.06)",
                            "display": "grid",
                            "gap": "6px",
                        },
                        children=[
                            html.Div(f"Smoothing: {smoothing_method}", style={"fontSize": "13px", "lineHeight": "1.5"}),
                            html.Div(f"Anomaly threshold: {anomaly_threshold}", style={"fontSize": "13px", "lineHeight": "1.5"}),
                            html.Div(f"Extreme-event rule: {extreme_rule}", style={"fontSize": "13px", "lineHeight": "1.5"}),
                        ],
                    ),
                ],
            )
        )

    return cards

app = Dash(__name__)
app.title = "Weather Analysis Dashboard"

app.layout = html.Div(
    style={
        "minHeight": "100vh",
        "padding": "28px 22px 48px 22px",
        "background": (
            "radial-gradient(circle at 10% 0%, rgba(211, 184, 124, 0.30), transparent 24%), "
            "radial-gradient(circle at 100% 10%, rgba(104, 147, 159, 0.18), transparent 22%), "
            "linear-gradient(180deg, #f4efe6 0%, #f3f1ed 44%, #edf2f1 100%)"
        ),
        "fontFamily": "Georgia, Cambria, Times New Roman, serif",
        "color": "#1d2a34",
    },
    children=[
        html.Div(
            style={"maxWidth": "1400px", "margin": "0 auto"},
            children=[
                html.Div(
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "minmax(0, 1.7fr) minmax(320px, 0.9fr)",
                        "gap": "18px",
                        "padding": "30px",
                        "marginBottom": "20px",
                        "borderRadius": "30px",
                        "background": "linear-gradient(135deg, #142028 0%, #1f3441 48%, #30586b 100%)",
                        "boxShadow": "0 26px 60px rgba(16, 24, 29, 0.16)",
                        "color": "#f5f2ec",
                    },
                    children=[
                        html.Div(
                            children=[
                                html.Div(
                                    "Operational view of cleaned weather data, exploratory analysis, trend diagnostics, and refinement outputs",
                                    style={
                                        "fontSize": "12px",
                                        "textTransform": "uppercase",
                                        "letterSpacing": "1.6px",
                                        "opacity": "0.72",
                                        "marginBottom": "14px",
                                    },
                                ),
                                html.H1(
                                    "Climate Intelligence Dashboard",
                                    style={
                                        "fontSize": "56px",
                                        "lineHeight": "0.95",
                                        "margin": "0 0 16px 0",
                                    },
                                ),
                                html.P(
                                    "This dashboard consolidates the project pipeline into a single decision surface: cleaned daily observations, seasonal structure, inter-annual variability, extreme-event diagnostics, and refinement recommendations for Mumbai, Delhi, Dehradun, and Jodhpur.",
                                    style={
                                        "fontSize": "18px",
                                        "lineHeight": "1.7",
                                        "maxWidth": "860px",
                                        "margin": "0 0 24px 0",
                                        "color": "rgba(245, 242, 236, 0.88)",
                                    },
                                ),
                                html.Div(
                                    style={
                                        "display": "grid",
                                        "gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
                                        "gap": "12px",
                                        "maxWidth": "780px",
                                    },
                                    children=[
                                        html.Div(
                                            style={
                                                "padding": "16px 18px",
                                                "borderRadius": "18px",
                                                "backgroundColor": "rgba(255,255,255,0.08)",
                                                "border": "1px solid rgba(255,255,255,0.12)",
                                            },
                                            children=[
                                                html.Div("Coverage window", style={"fontSize": "12px", "opacity": "0.68", "marginBottom": "4px"}),
                                                html.Div("2000-2024", style={"fontSize": "24px", "fontWeight": "bold"}),
                                            ],
                                        ),
                                        html.Div(
                                            style={
                                                "padding": "16px 18px",
                                                "borderRadius": "18px",
                                                "backgroundColor": "rgba(255,255,255,0.08)",
                                                "border": "1px solid rgba(255,255,255,0.12)",
                                            },
                                            children=[
                                                html.Div("City portfolio", style={"fontSize": "12px", "opacity": "0.68", "marginBottom": "4px"}),
                                                html.Div("4", style={"fontSize": "24px", "fontWeight": "bold"}),
                                            ],
                                        ),
                                        html.Div(
                                            style={
                                                "padding": "16px 18px",
                                                "borderRadius": "18px",
                                                "backgroundColor": "rgba(255,255,255,0.08)",
                                                "border": "1px solid rgba(255,255,255,0.12)",
                                            },
                                            children=[
                                                html.Div("Analytical layers", style={"fontSize": "12px", "opacity": "0.68", "marginBottom": "4px"}),
                                                html.Div("Reports + Refinement", style={"fontSize": "20px", "fontWeight": "bold"}),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        html.Div(
                            style={
                                "display": "flex",
                                "flexDirection": "column",
                                "justifyContent": "space-between",
                                "background": "linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0.07))",
                                "padding": "24px",
                                "borderRadius": "24px",
                                "border": "1px solid rgba(255,255,255,0.12)",
                            },
                            children=[
                                html.Div(
                                    [
                                        html.Div("Control Panel", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "1.6px", "opacity": "0.72", "marginBottom": "10px"}),
                                        html.H3("Scope the dashboard view", style={"margin": "0 0 8px 0", "fontSize": "28px"}),
                                        html.P(
                                            "Apply a city filter to update the executive summary, climate diagnostics, extreme-event panels, and refinement recommendations in one pass.",
                                            style={"margin": "0 0 18px 0", "lineHeight": "1.6", "color": "rgba(245,242,236,0.84)"},
                                        ),
                                    ]
                                ),
                                html.Label("City Filter", style={"display": "block", "fontWeight": "bold", "marginBottom": "8px", "fontSize": "14px"}),
                                dcc.Dropdown(
                                    id="city-filter",
                                    options=[{"label": city, "value": city} for city in available_cities],
                                    value=available_cities,
                                    multi=True,
                                    placeholder="Select cities",
                                    style={"color": "#1d2a34", "marginBottom": "18px"},
                                ),
                                html.Div(
                                    style={
                                        "padding": "16px 18px",
                                        "borderRadius": "18px",
                                        "backgroundColor": "rgba(11, 18, 22, 0.18)",
                                    },
                                    children=[
                                        html.Div("Included modules", style={"fontSize": "12px", "opacity": "0.70", "marginBottom": "6px"}),
                                        html.Div("Cleaned observations, exploratory summaries, trend signals, and refinement outputs", style={"lineHeight": "1.55"}),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                section_heading(
                    "Executive Summary",
                    "Portfolio-level view of the selected climate records",
                    "The KPI row focuses on scope and event activity only. City-level averages are separated below so multi-city selections remain interpretable.",
                ),
                html.Div(
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
                        "gap": "16px",
                        "marginBottom": "28px",
                    },
                    children=[
                        html.Div(id="card-observations", style={**CARD_BASE_STYLE, "background": "linear-gradient(135deg, #f8f3e4, #ebd8ac)"}),
                        html.Div(id="card-temp", style={**CARD_BASE_STYLE, "background": "linear-gradient(135deg, #f8e2c7, #dca36d)"}),
                        html.Div(id="card-rain", style={**CARD_BASE_STYLE, "background": "linear-gradient(135deg, #dceaf1, #9dbfd0)"}),
                        html.Div(id="card-extremes", style={**CARD_BASE_STYLE, "background": "linear-gradient(135deg, #dcead8, #a9c59d)"}),
                    ],
                ),
                section_heading(
                    "City Benchmarks",
                    "Separate city-level averages and refinement context",
                    "Each card below preserves city-level meaning by keeping temperature, rainfall, event counts, and method recommendations independent.",
                ),
                html.Div(
                    id="city-summary-grid",
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(280px, 1fr))",
                        "gap": "16px",
                        "marginBottom": "28px",
                    },
                ),
                dcc.Tabs(
                    id="dashboard-tabs",
                    value="climate",
                    parent_style={"marginBottom": "22px"},
                    children=[
                        dcc.Tab(
                            label="Climate Baseline",
                            value="climate",
                            style=TAB_STYLE,
                            selected_style=TAB_SELECTED_STYLE,
                            children=[
                                html.Div(
                                    style={"paddingTop": "16px"},
                                    children=[
                                        section_heading(
                                            "Climate Baseline",
                                            "Seasonal profiles and long-range signal stability",
                                            "These panels establish the expected monthly climate pattern and compare it with year-to-year change and dispersion.",
                                        ),
                                        html.Div(
                                            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "18px", "marginBottom": "18px"},
                                            children=[
                                                html.Div(
                                                    style={**GRAPH_STYLE, "padding": "16px"},
                                                    children=[
                                                        panel_header("Seasonality", "Monthly temperature profile", "Mean monthly temperature by city from the cleaned daily records."),
                                                        dcc.Graph(id="seasonal-temp-chart", config={"displayModeBar": False}),
                                                    ],
                                                ),
                                                html.Div(
                                                    style={**GRAPH_STYLE, "padding": "16px"},
                                                    children=[
                                                        panel_header("Seasonality", "Monthly precipitation profile", "Average monthly precipitation totals aligned to the selected city scope."),
                                                        dcc.Graph(id="seasonal-rain-chart", config={"displayModeBar": False}),
                                                    ],
                                                ),
                                            ],
                                        ),
                                        html.Div(
                                            style={"display": "grid", "gridTemplateColumns": "1.35fr 1fr", "gap": "18px", "marginBottom": "8px"},
                                            children=[
                                                html.Div(
                                                    style={**GRAPH_STYLE, "padding": "16px"},
                                                    children=[
                                                        panel_header("Inter-Annual Trend", "Temperature and precipitation trajectory", "Annual means and totals reveal the long-range signal across the selected cities."),
                                                        dcc.Graph(id="yearly-trend-chart", config={"displayModeBar": False}),
                                                    ],
                                                ),
                                                html.Div(
                                                    style={**GRAPH_STYLE, "padding": "16px"},
                                                    children=[
                                                        panel_header("Variability", "Relative year-to-year dispersion", "Coefficient-of-variation metrics compare the stability of temperature, precipitation, dew point, and wind."),
                                                        dcc.Graph(id="variability-chart", config={"displayModeBar": False}),
                                                    ],
                                                ),
                                            ],
                                        ),
                                    ],
                                )
                            ],
                        ),
                        dcc.Tab(
                            label="Extreme Events",
                            value="extremes",
                            style=TAB_STYLE,
                            selected_style=TAB_SELECTED_STYLE,
                            children=[
                                html.Div(
                                    style={"paddingTop": "16px"},
                                    children=[
                                        section_heading(
                                            "Extreme Event Diagnostics",
                                            "Heat, rainfall stress, and monthly thermal concentration",
                                            "This view focuses on the event-detection layer and avoids mixing it with baseline climate summaries.",
                                        ),
                                        html.Div(
                                            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "18px", "marginBottom": "18px"},
                                            children=[
                                                html.Div(
                                                    style={**GRAPH_STYLE, "padding": "16px"},
                                                    children=[
                                                        panel_header("Extreme Heat", "Heatwave incidence under the selected rule", "Counts are derived from the best city-specific rule identified in the refinement workflow."),
                                                        dcc.Graph(id="heatwave-chart", config={"displayModeBar": False}),
                                                    ],
                                                ),
                                                html.Div(
                                                    style={**GRAPH_STYLE, "padding": "16px"},
                                                    children=[
                                                        panel_header("Rainfall Extremes", "Heavy and extreme rainfall incidence", "Heavy-rain and extreme-rain day counts are shown together for direct comparison."),
                                                        dcc.Graph(id="rain-extreme-chart", config={"displayModeBar": False}),
                                                    ],
                                                ),
                                            ],
                                        ),
                                        html.Div(
                                            style={"display": "grid", "gridTemplateColumns": "1.35fr 1fr", "gap": "18px", "marginBottom": "8px"},
                                            children=[
                                                html.Div(
                                                    style={**GRAPH_STYLE, "padding": "16px"},
                                                    children=[
                                                        panel_header("Thermal Pattern", "Monthly temperature heatmap", "A compact city-by-month view of the annual thermal profile."),
                                                        dcc.Graph(id="heatmap-chart", config={"displayModeBar": False}),
                                                    ],
                                                ),
                                                html.Div(
                                                    style={**GRAPH_STYLE, "padding": "16px"},
                                                    children=[
                                                        panel_header("Smoothing Selection", "Best-performing smoothing method", "Noise-reduction performance from the refinement workflow by city."),
                                                        dcc.Graph(id="method-bar-chart", config={"displayModeBar": False}),
                                                    ],
                                                ),
                                            ],
                                        ),
                                    ],
                                )
                            ],
                        ),
                        dcc.Tab(
                            label="Refinement Summary",
                            value="refinement",
                            style=TAB_STYLE,
                            selected_style=TAB_SELECTED_STYLE,
                            children=[
                                html.Div(
                                    style={"paddingTop": "16px"},
                                    children=[
                                        html.Div(
                                            style={**PANEL_STYLE, "padding": "22px"},
                                            children=[
                                                section_heading(
                                                    "Refinement Recommendations",
                                                    "Production summary of selected methods by city",
                                                    "This table consolidates the preferred smoothing method, anomaly threshold, and extreme-event rule produced by the refinement modules.",
                                                ),
                                                dash_table.DataTable(
                                                    id="comparison-table",
                                                    page_size=10,
                                                    style_table={"overflowX": "auto"},
                                                    style_cell={
                                                        "padding": "12px",
                                                        "textAlign": "left",
                                                        "fontFamily": "Georgia, Cambria, Times New Roman, serif",
                                                        "backgroundColor": "rgba(255,255,255,0.55)",
                                                        "border": "none",
                                                        "fontSize": "14px",
                                                        "minWidth": "120px",
                                                    },
                                                    style_header={
                                                        "fontWeight": "bold",
                                                        "backgroundColor": "#dfd3bd",
                                                        "border": "none",
                                                        "color": "#2d3a34",
                                                    },
                                                    style_data={"whiteSpace": "normal", "height": "auto"},
                                                ),
                                            ],
                                        ),
                                    ],
                                )
                            ],
                        ),
                    ],
                ),
            ],
        )
    ],
)


def add_dashboard_theme(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font={"family": "Georgia, Cambria, Times New Roman, serif", "color": "#1f2a36"},
        title={"x": 0.03},
        margin={"l": 58, "r": 28, "t": 42, "b": 62},
        legend={"orientation": "h", "yanchor": "top", "y": -0.18, "xanchor": "left", "x": 0, "title": {"text": ""}},
        hoverlabel={"bgcolor": "#ffffff"},
    )
    fig.update_xaxes(automargin=True, tickangle=0)
    fig.update_yaxes(automargin=True)
    return fig


def empty_figure(title):
    fig = px.scatter(title=title)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.add_annotation(
        text="Select at least one city to view this chart.",
        showarrow=False,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        font={"size": 16},
    )
    return add_dashboard_theme(fig)


def metric_card(title, value, subtitle):
    return [
        html.Div(title, style={"fontWeight": "bold", "fontSize": "15px", "marginBottom": "8px"}),
        html.Div(value, style={"fontSize": "34px", "fontWeight": "bold", "lineHeight": "1.1"}),
        html.Div(subtitle, style={"marginTop": "8px", "fontSize": "13px", "opacity": "0.72"}),
    ]


def seasonal_temperature_figure(filtered_monthly):
    if filtered_monthly.empty:
        return empty_figure("Seasonal Temperature Cycle")

    fig = px.line(
        filtered_monthly,
        x="MONTH",
        y="TEMP_MEAN",
        color="CITY",
        color_discrete_map=CITY_COLORS,
        markers=True,
        title="Seasonal Temperature Cycle",
    )
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(title="Temperature (C)")
    return add_dashboard_theme(fig)


def seasonal_rain_figure(filtered_monthly):
    if filtered_monthly.empty:
        return empty_figure("Seasonal Rainfall Pattern")

    fig = px.line(
        filtered_monthly,
        x="MONTH",
        y="PRCP_MEAN",
        color="CITY",
        color_discrete_map=CITY_COLORS,
        markers=True,
        title="Seasonal Rainfall Pattern",
    )
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(title="Average Monthly Rainfall (mm)")
    return add_dashboard_theme(fig)


def yearly_trend_figure(filtered_yearly):
    if filtered_yearly.empty:
        return empty_figure("Inter-Annual Temperature Trend")

    fig = go.Figure()
    for city in filtered_yearly["CITY"].dropna().unique():
        city_df = filtered_yearly[filtered_yearly["CITY"] == city]
        fig.add_trace(
            go.Scatter(
                x=city_df["YEAR"],
                y=city_df["TEMP_MEAN"],
                mode="lines+markers",
                name=f"{city} Temperature",
                line={"color": CITY_COLORS.get(city)},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=city_df["YEAR"],
                y=city_df["PRCP_TOTAL"],
                mode="lines",
                name=f"{city} Rainfall",
                line={"color": CITY_COLORS.get(city), "dash": "dot"},
                yaxis="y2",
                opacity=0.55,
            )
        )

    fig.update_layout(
        title="Inter-Annual Temperature and Rainfall Trend",
        yaxis={"title": "Temperature (C)"},
        yaxis2={"title": "Rainfall (mm)", "overlaying": "y", "side": "right"},
    )
    fig.update_xaxes(tickmode="linear")
    return add_dashboard_theme(fig)


def variability_figure(filtered_variability):
    if filtered_variability.empty:
        return empty_figure("Yearly Variability")

    var_long = filtered_variability.melt(
        id_vars="CITY",
        value_vars=["TEMP_CV", "PRCP_CV", "DEW_CV", "WIND_CV"],
        var_name="Variable",
        value_name="Coefficient of Variation",
    )
    fig = px.bar(
        var_long,
        x="CITY",
        y="Coefficient of Variation",
        color="Variable",
        barmode="group",
        title="Yearly Variability by Climate Variable",
    )
    return add_dashboard_theme(fig)


def heatwave_figure(filtered_extreme):
    if filtered_extreme.empty:
        return empty_figure("Heatwave Days by Best Rule")

    fig = px.bar(
        filtered_extreme,
        x="City",
        y="Heatwave Days",
        color="City",
        color_discrete_map=CITY_COLORS,
        title="Heatwave Days Under Best Extreme-Event Rule",
    )
    fig.update_traces(hovertemplate="%{x}<br>Heatwave days: %{y}<extra></extra>")
    return add_dashboard_theme(fig)


def rain_extreme_figure(filtered_extreme):
    if filtered_extreme.empty:
        return empty_figure("Rain Extremes by Best Rule")

    fig = px.bar(
        filtered_extreme,
        x="City",
        y=["Heavy Rain Days", "Extreme Rain Days"],
        barmode="group",
        title="Heavy and Extreme Rain Days",
    )
    return add_dashboard_theme(fig)


def monthly_heatmap_figure(filtered_monthly):
    if filtered_monthly.empty:
        return empty_figure("Monthly Temperature Heatmap")

    pivot = filtered_monthly.pivot_table(index="CITY", columns="MONTH", values="TEMP_MEAN", aggfunc="mean")
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="YlOrRd",
        labels={"x": "Month", "y": "City", "color": "Temp (C)"},
        title="Monthly Temperature Heatmap",
    )
    return add_dashboard_theme(fig)


def smoothing_bar_figure(filtered_smoothing):
    if filtered_smoothing.empty:
        return empty_figure("Best Smoothing by City")

    fig = px.bar(
        filtered_smoothing,
        x="City",
        y="Noise Reduction (%)",
        color="Method",
        title="Best Smoothing Choice by City",
    )
    fig.update_traces(hovertemplate="%{x}<br>Noise reduction: %{y:.2f}%<extra></extra>")
    return add_dashboard_theme(fig)


@app.callback(
    Output("card-observations", "children"),
    Output("card-temp", "children"),
    Output("card-rain", "children"),
    Output("card-extremes", "children"),
    Output("city-summary-grid", "children"),
    Output("seasonal-temp-chart", "figure"),
    Output("seasonal-rain-chart", "figure"),
    Output("yearly-trend-chart", "figure"),
    Output("variability-chart", "figure"),
    Output("heatwave-chart", "figure"),
    Output("rain-extreme-chart", "figure"),
    Output("heatmap-chart", "figure"),
    Output("method-bar-chart", "figure"),
    Output("comparison-table", "data"),
    Output("comparison-table", "columns"),
    Input("city-filter", "value"),
)
def update_dashboard(selected_cities):
    if not selected_cities:
        return (
            metric_card("Selected Cities", "0", "No cities selected"),
            metric_card("Daily Records", "0", "No active observation rows"),
            metric_card("Coverage Window", "N/A", "Select at least one city"),
            metric_card("Flagged Events", "0", "Heatwave and heavy-rain days"),
            [],
            empty_figure("Seasonal Temperature Cycle"),
            empty_figure("Seasonal Rainfall Pattern"),
            empty_figure("Inter-Annual Temperature Trend"),
            empty_figure("Yearly Variability"),
            empty_figure("Heatwave Days by Best Rule"),
            empty_figure("Rain Extremes by Best Rule"),
            empty_figure("Monthly Temperature Heatmap"),
            empty_figure("Best Smoothing by City"),
            refinement_summary_df.to_dict("records") if not refinement_summary_df.empty else [],
            [{"name": col, "id": col} for col in refinement_summary_df.columns],
        )

    filtered_analysis = analysis_df[analysis_df["CITY"].isin(selected_cities)].copy()
    filtered_monthly = monthly_df[monthly_df["CITY"].isin(selected_cities)].copy() if not monthly_df.empty else monthly_df
    filtered_yearly = yearly_df[yearly_df["CITY"].isin(selected_cities)].copy() if not yearly_df.empty else yearly_df
    filtered_variability = variability_df[variability_df["CITY"].isin(selected_cities)].copy() if not variability_df.empty else variability_df
    filtered_extreme = extreme_df[extreme_df["City"].isin(selected_cities)].copy() if not extreme_df.empty else extreme_df
    filtered_smoothing = smoothing_df[smoothing_df["City"].isin(selected_cities)].copy() if not smoothing_df.empty else smoothing_df
    filtered_summary = refinement_summary_df[refinement_summary_df["City"].isin(selected_cities)].copy() if not refinement_summary_df.empty else refinement_summary_df

    heatwave_days = int(filtered_analysis["HEATWAVE_DAY"].fillna(0).sum())
    heavy_rain_days = int(filtered_analysis["HEAVY_RAIN_DAY"].fillna(0).sum())
    extreme_rain_days = int(filtered_analysis["EXTREME_RAIN_DAY"].fillna(0).sum())
    date_min = filtered_analysis["DATE"].min()
    date_max = filtered_analysis["DATE"].max()
    coverage_label = "N/A"
    if pd.notna(date_min) and pd.notna(date_max):
        coverage_label = f"{date_min.year}-{date_max.year}"
    city_cards = build_city_snapshot_cards(selected_cities, filtered_analysis, filtered_summary)

    return (
        metric_card("Selected Cities", f"{len(selected_cities)}", "Active comparison set"),
        metric_card("Daily Records", f"{len(filtered_analysis):,}", "Rows in the filtered daily dataset"),
        metric_card("Coverage Window", coverage_label, "Observation span for the selected records"),
        metric_card("Flagged Events", f"{heatwave_days + heavy_rain_days:,}", f"Heatwave: {heatwave_days:,} | Heavy rain: {heavy_rain_days:,} | Extreme rain: {extreme_rain_days:,}"),
        city_cards,
        seasonal_temperature_figure(filtered_monthly),
        seasonal_rain_figure(filtered_monthly),
        yearly_trend_figure(filtered_yearly),
        variability_figure(filtered_variability),
        heatwave_figure(filtered_extreme),
        rain_extreme_figure(filtered_extreme),
        monthly_heatmap_figure(filtered_monthly),
        smoothing_bar_figure(filtered_smoothing),
        filtered_summary.to_dict("records") if not filtered_summary.empty else [],
        [{"name": col, "id": col} for col in filtered_summary.columns],
    )


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
