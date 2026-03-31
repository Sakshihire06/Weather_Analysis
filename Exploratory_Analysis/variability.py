import os
os.makedirs("reports/figures", exist_ok=True)

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

from .main_eda import load_all_cities
def yearly_variability(df):

    # Aggregate to yearly level
    yearly = df.groupby(["CITY", "YEAR"]).agg(
        TEMP_MEAN=("TEMP_C", "mean"),
        PRCP_TOTAL=("PRCP_MM", "sum"),
        DEW_MEAN=("DEWP_C", "mean"),
        WIND_MEAN=("WDSP_MS", "mean"),
    ).reset_index()

    # Compute variability per city
    var = yearly.groupby("CITY").agg(
        TEMP_STD=("TEMP_MEAN", "std"),
        PRCP_STD=("PRCP_TOTAL", "std"),
        DEW_STD=("DEW_MEAN", "std"),
        WIND_STD=("WIND_MEAN", "std"),

        TEMP_CV=("TEMP_MEAN", lambda x: x.std()/x.mean()),
        PRCP_CV=("PRCP_TOTAL", lambda x: x.std()/x.mean()),
        DEW_CV=("DEW_MEAN", lambda x: x.std()/x.mean()),
        WIND_CV=("WIND_MEAN", lambda x: x.std()/x.mean()),
    ).reset_index()

    return yearly, var
def variability_table(var):
    print("\n📊 Yearly Variability Summary (CV + STD)\n")
    print(var.round(3))

    var.to_csv("reports/yearly_variability.csv", index=False)
def plot_variability_bar(var):
    import plotly.express as px

    var_long = var.melt(
        id_vars="CITY",
        value_vars=["TEMP_CV", "PRCP_CV", "DEW_CV", "WIND_CV"],
        var_name="VARIABLE",
        value_name="CV"
    )

    fig = px.bar(
        var_long,
        x="CITY",
        y="CV",
        color="VARIABLE",
        barmode="group",
        template="plotly_white",
        title="Yearly Variability Comparison (CV)"
    )

    fig.update_layout(
        xaxis_title="City",
        yaxis_title="Coefficient of Variation"
    )

    fig.write_html("reports/figures/yearly_variability_bar.html")
    fig.show()
def plot_yearly_box(yearly):
    import plotly.express as px

    yearly_long = yearly.melt(
        id_vars=["CITY", "YEAR"],
        value_vars=["TEMP_MEAN", "PRCP_TOTAL", "DEW_MEAN", "WIND_MEAN"],
        var_name="VARIABLE",
        value_name="VALUE"
    )

    fig = px.box(
        yearly_long,
        x="CITY",
        y="VALUE",
        color="CITY",
        facet_row="VARIABLE",
        template="plotly_white",
        title="Yearly Distribution of Climate Variables"
    )

    # Clean look (like before)
    fig.update_yaxes(matches=None)

    for annotation in fig.layout.annotations:
        annotation.text = ""

    fig.update_layout(height=900)

    fig.write_html("reports/figures/yearly_variability_box.html")
    fig.show()
if __name__ == "__main__":
    df = load_all_cities()

    yearly, var = yearly_variability(df)

    variability_table(var)
    plot_variability_bar(var)
    plot_yearly_box(yearly)