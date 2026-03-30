import os
os.makedirs("reports/figures", exist_ok=True)

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

from .main_eda import load_all_cities


def prepare_monthly_data():
    df = load_all_cities()

    monthly_yearly = df.groupby(["CITY", "YEAR", "MONTH"]).agg(
        TEMP_MEAN=("TEMP_C", "mean"),
        PRCP_TOTAL=("PRCP_MM", "sum"),
        MAX_TEMP=("MAX_C","max"),
        MIN_TEMP=("MIN_C","min"),
        DEW_MEAN=("DEWP_C","mean"),
        WIND_SPEED=("WDSP_MS","mean"),
    ).reset_index()

    seasonal = monthly_yearly.groupby(["CITY", "MONTH"]).agg(
        TEMP_MEAN=("TEMP_MEAN", "mean"),
        PRCP_MEAN=("PRCP_TOTAL", "mean"),
        MAX_TEMP=("MAX_TEMP","max"),
        MIN_TEMP=("MIN_TEMP","min"),
        DEW_MEAN=("DEW_MEAN","mean"),
        WIND_SPEED=("WIND_SPEED","mean"),
        
    ).reset_index()

    return df, seasonal
def print_numerical_summary(seasonal):
    print(" NUMERICAL SUMMARY (Monthly)")
    print(seasonal.describe())

def save_monthly_table(seasonal):
    seasonal.to_csv("reports/monthly_summary.csv", index=False)
    print("Saved monthly summary table.")

def plot_temperature(seasonal):
    plt.figure()
    for city in seasonal["CITY"].unique():
        subset = seasonal[seasonal["CITY"] == city]
        plt.plot(subset["MONTH"], subset["TEMP_MEAN"], label=city)

    plt.title("Seasonal Temperature Cycle")
    plt.xlabel("Month")
    plt.ylabel("Temperature (°C)")
    plt.legend()
    plt.savefig("reports/figures/temp_seasonality.png")
    plt.show()


def plot_rainfall(seasonal):
    plt.figure()
    for city in seasonal["CITY"].unique():
        subset = seasonal[seasonal["CITY"] == city]
        plt.plot(subset["MONTH"], subset["PRCP_MEAN"], label=city)

    plt.title("Seasonal Rainfall Pattern")
    plt.xlabel("Month")
    plt.ylabel("Total Precipitation (mm)")
    plt.legend()
    plt.savefig("reports/figures/rainfall_seasonality.png")
    plt.show()

def plot_humidity(seasonal):

    for city in seasonal["CITY"].unique():
        subset = seasonal[seasonal["CITY"] == city]

        plt.figure()
        plt.plot(subset["MONTH"], subset["TEMP_MEAN"], label="Temp")
        plt.plot(subset["MONTH"], subset["DEW_MEAN"], label="Dew Point")

        plt.title(f"{city}'s Humidity")
        plt.legend()
        plt.savefig(f"reports/figures/{city}_humidity.png")
        plt.show()

def interactive_dashboard(df):
    import plotly.express as px

    df_long = df.melt(
        id_vars=["DATE", "CITY"],
        value_vars=["TEMP_C", "PRCP_MM", "DEWP_C", "WDSP_MS"],
        var_name="VARIABLE",
        value_name="VALUE"
    )

    fig = px.line(
        df_long,
        x="DATE",
        y="VALUE",
        color="CITY",
        animation_frame="VARIABLE",
        title="Interactive Multi-variable Weather Dashboard")

    fig.write_html("reports/figures/full_dashboard.html")
    fig.show()

if __name__ == "__main__":
    df, seasonal = prepare_monthly_data()

    print_numerical_summary(seasonal)
    save_monthly_table(seasonal)

    plot_temperature(seasonal)
    plot_rainfall(seasonal)
    plot_humidity(seasonal)
    interactive_dashboard(df)


    