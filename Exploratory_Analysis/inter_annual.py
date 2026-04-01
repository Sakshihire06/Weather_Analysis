import os
os.makedirs("reports/figures", exist_ok=True)

import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from main_eda import load_all_cities

def prepare_yearly_data():
    
    df = load_all_cities() 
    yearly = df.groupby(["CITY", "YEAR"]).agg(
        TEMP_MEAN=("TEMP_C", "mean"),
        PRCP_TOTAL=("PRCP_MM", "sum"),
        MAX_TEMP=("MAX_C", "max"),
        MIN_TEMP=("MIN_C", "min"),
        DEW_MEAN=("DEWP_C", "mean"),
        WIND_SPEED=("WDSP_MS", "mean"),
    ).reset_index()

    return df, yearly
def print_yearly_summary(yearly):
    print(" INTERANNUAL SUMMARY")
    print(yearly.describe())

def save_yearly_table(yearly):
    yearly.to_csv("reports/yearly_summary.csv", index=False)
    print("Saved yearly summary table.")

def plot_temperature_trend(yearly):
    plt.figure()

    for city in yearly["CITY"].unique():
        subset = yearly[yearly["CITY"] == city]
        plt.plot(subset["YEAR"], subset["TEMP_MEAN"], label=city)

    plt.title("Interannual Temperature Trend")
    plt.xlabel("Year")
    plt.ylabel("Mean Temperature (°C)")
    plt.legend()
    plt.savefig("reports/figures/temp_trend.png")
    plt.show()
def plot_rainfall_trend(yearly):
    plt.figure()

    for city in yearly["CITY"].unique():
        subset = yearly[yearly["CITY"] == city]
        plt.plot(subset["YEAR"], subset["PRCP_TOTAL"], label=city)

    plt.title("Interannual Rainfall Variability")
    plt.xlabel("Year")
    plt.ylabel("Total Rainfall (mm)")
    plt.legend()
    plt.savefig("reports/figures/rainfall_trend.png")
    plt.show()
def interactive_yearly(yearly):

    yearly_long = yearly.melt(
        id_vars=["YEAR", "CITY"],
        value_vars=["TEMP_MEAN", "PRCP_TOTAL", "DEW_MEAN", "WIND_SPEED"],
        var_name="VARIABLE",
        value_name="VALUE"
    )
    yearly_long["VARIABLE"] = pd.Categorical(
        yearly_long["VARIABLE"],
        categories=["WIND_SPEED", "DEW_MEAN", "PRCP_TOTAL", "TEMP_MEAN"],
        ordered=True
    )

    label_map = {
        "TEMP_MEAN": "Temperature (°C)",
        "PRCP_TOTAL": "Rainfall (mm)",
        "DEW_MEAN": "Dew Point (°C)",
        "WIND_SPEED": "Wind Speed (m/s)"
    }

    fig = px.line(
        yearly_long,
        x="YEAR",
        y="VALUE",
        color="CITY",
        facet_row="VARIABLE",
        labels=label_map,
        markers=True,
        template="plotly_white",
        title="Interannual Climate Trends"
    )
    for ann in fig.layout.annotations:
        ann.text = ann.text.split("=")[-1]

    fig.update_yaxes(matches=None)

    fig.update_layout(
        height=1000,
        xaxis_title="Year",
        legend_title="City"
    )

    fig.show()
if __name__ == "__main__":
    df, yearly = prepare_yearly_data()

    print_yearly_summary(yearly)
    save_yearly_table(yearly)

    plot_temperature_trend(yearly)
    plot_rainfall_trend(yearly)
    interactive_yearly(yearly)

  
