import os
os.makedirs("reports/figures", exist_ok=True)

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from main_eda import load_all_cities

def prepare_variability():
    
    df = load_all_cities() 
    yearly = df.groupby(["CITY", "YEAR"]).agg(
        TEMP_MEAN=("TEMP_C", "mean"),
        PRCP_TOTAL=("PRCP_MM", "sum"),
        DEW_MEAN=("DEWP_C", "mean"),
        WIND_MEAN=("WDSP_MS", "mean"),
    ).reset_index()

    
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
    print("Yearly Variability Summary (CV + STD)\n")
    print(var.round(3))

    var.to_csv("reports/yearly_variability.csv", index=False)
def plot_variability_bar(var):
    plt.figure(figsize=(10, 6))
    
    var_long = var.melt(
        id_vars="CITY",
        value_vars=["TEMP_CV", "PRCP_CV", "DEW_CV", "WIND_CV"],
        var_name="VARIABLE",
        value_name="CV"
    )
    sns.barplot(data=var_long, x="CITY", y="CV", hue="VARIABLE")

    plt.title("Yearly Variability Comparison (Coefficient of Variation)")
    plt.ylabel("Coefficient of Variation")
    plt.xlabel("City")
    plt.legend(title="Variable", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig("reports/figures/yearly_variability_bar.png", dpi=300)
    plt.show()
def plot_yearly_box(yearly):
    # Melt the data
    yearly_long = yearly.melt(
        id_vars=["CITY", "YEAR"],
        value_vars=["TEMP_MEAN", "PRCP_TOTAL", "DEW_MEAN", "WIND_MEAN"],
        var_name="VARIABLE",
        value_name="VALUE"
    )

    g = sns.catplot(
        data=yearly_long, 
        x="CITY", 
        y="VALUE", 
        hue="CITY",
        row="VARIABLE", 
        kind="box", 
        height=3, 
        aspect=3,
        sharey=False  
    )

    g.set_titles("{row_name}") 
    g.fig.suptitle("Yearly Distribution of Climate Variables", y=1.02)
    
    plt.savefig("reports/figures/yearly_variability_box.png", dpi=300, bbox_inches='tight')
    plt.show()


if __name__ == "__main__":
    yearly_df, var_df = prepare_variability()

    variability_table(var_df)
    plot_variability_bar(var_df)
    plot_yearly_box(yearly_df)
