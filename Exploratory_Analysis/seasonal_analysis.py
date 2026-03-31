import os
os.makedirs("reports/figures", exist_ok=True)

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from main_eda import load_all_cities

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

def interactive_monthly(seasonal):
    import plotly.express as px

    seasonal_long = seasonal.melt(
        id_vars=["MONTH", "CITY"],
        value_vars=["TEMP_MEAN", "PRCP_MEAN", "DEW_MEAN", "WIND_SPEED"],
        var_name="VARIABLE",
        value_name="VALUE"
    )

    seasonal_long = seasonal_long.sort_values("MONTH")

    fig = px.line(
        seasonal_long,
        x="MONTH",
        y="VALUE",
        color="CITY",
        facet_row="VARIABLE",
        markers=True,
        template="plotly_white",
        title="Monthly Seasonal Climate Patterns"
    )

    
    fig.for_each_xaxis(lambda x: x.update(
        showticklabels=True,
        tickmode="array",
        tickvals=list(range(1, 13)),
        ticktext=[
            "Jan","Feb","Mar","Apr","May","Jun",
            "Jul","Aug","Sep","Oct","Nov","Dec"
        ]
    ))

   
    fig.update_yaxes(matches=None, side="left")

    for annotation in fig.layout.annotations:
        annotation.text = ""

    
    label_map = {
        "TEMP_MEAN": "Temperature (°C)",
        "PRCP_MEAN": "Rainfall (mm)",
        "DEW_MEAN": "Dew Point (°C)",
        "WIND_SPEED": "Wind Speed (m/s)"
    }

    
    variables = seasonal_long["VARIABLE"].unique()

    
    variables = variables[::-1]

    # Assign labels correctly
    for i, var in enumerate(variables):
        fig.layout[f'yaxis{i+1}'].title.text = label_map[var]

    
    for i in range(2, 10):
        axis = f'yaxis{i}'
        if axis in fig.layout:
            fig.layout[axis].side = "left"

    fig.update_layout(
        height=1000,
        xaxis_title="Month",
        legend_title="City",
        margin=dict(l=60, r=40, t=60, b=60)
    )

    fig.write_html("reports/figures/monthly_dashboard_facets.html")
    fig.show()
if __name__ == "__main__":
    df, seasonal = prepare_monthly_data()

    print_numerical_summary(seasonal)
    save_monthly_table(seasonal)

    plot_temperature(seasonal)
    plot_rainfall(seasonal)
    plot_humidity(seasonal)
    interactive_monthly(seasonal)


    