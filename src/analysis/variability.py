    seasonal = monthly_yearly.groupby(["CITY", "MONTH"]).agg(
        PRCP_STD=("PRCP_TOTAL", "std")
        TEMP_STD=("TEMP_MEAN", "std"),
def boxplot_temperature(df):
    plt.figure()
    sns.boxplot(data=df, x="MONTH", y="TEMP_C")
    plt.title("Monthly Temperature Distribution")
    plt.savefig("../../reports/figures/temp_boxplot.png")
    plt.show()