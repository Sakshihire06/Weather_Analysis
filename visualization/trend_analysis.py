import sys
import os

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
)
from cleaned_data.dehradun_cleaned import get_cleaned_data as get_mumbai_cleaned
from cleaned_data.delhi_cleaned import get_cleaned_data as get_delhi_cleaned
from cleaned_data.jodhpur_cleaned import get_cleaned_data as get_jodhpur_cleaned
from cleaned_data.mumbai_cleaned import get_cleaned_data as get_dehradun_cleaned

mumbai   = get_mumbai_cleaned()
delhi    = get_delhi_cleaned()
dehradun = get_dehradun_cleaned()
jodhpur  = get_jodhpur_cleaned()


import pandas as pd
import plotly.express as px

CITY_COLORS = {
    'Mumbai': '#1f77b4',
    'Delhi': '#d62728',
    'Dehradun': '#2ca02c',
    'Jodhpur': "#E06C06"}

def prepare_analysis_df(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'CITY', 'YEAR', 'MONTH', 'SEASON',
        'TEMP', 'DEWP', 'PRCP', 'WDSP', 'MAX', 'MIN',
        'HEATWAVE_DAY', 'HEAVY_RAIN_DAY',
        'VERY_HEAVY_RAIN_DAY', 'EXTREME_RAIN_DAY']
    cols = [c for c in cols if c in df.columns]

    df = df[cols].copy()
    df['TEMP_RANGE'] = df['MAX'] - df['MIN']
    return df

def create_monthly_df(df: pd.DataFrame) -> pd.DataFrame:
    monthly = (df.groupby(['CITY', 'YEAR', 'MONTH'], as_index=False).agg({
            'TEMP': 'mean',
            'DEWP': 'mean',
            'WDSP': 'mean',
            'PRCP': 'sum',
            'MAX': 'mean',
            'MIN': 'mean',
            'HEATWAVE_DAY': 'sum',
            'HEAVY_RAIN_DAY': 'sum',
            'VERY_HEAVY_RAIN_DAY': 'sum',
            'EXTREME_RAIN_DAY': 'sum'}))

    monthly = monthly.rename(columns={
        'TEMP': 'TEMP_mean',
        'PRCP': 'PRCP_sum',
        'HEATWAVE_DAY': 'HEATWAVE_COUNT',
        'HEAVY_RAIN_DAY': 'HEAVY_RAIN_COUNT',
        'VERY_HEAVY_RAIN_DAY': 'VERY_HEAVY_RAIN_COUNT',
        'EXTREME_RAIN_DAY': 'EXTREME_RAIN_COUNT'})

    return monthly

def create_yearly_df(df: pd.DataFrame) -> pd.DataFrame:
    yearly = (df.groupby(['CITY', 'YEAR'], as_index=False).agg({
            'TEMP': 'mean',
            'PRCP': 'sum',
            'MAX': 'max',
            'MIN': 'min',
            'HEATWAVE_DAY': 'sum',
            'HEAVY_RAIN_DAY': 'sum'}))

    yearly = yearly.rename(columns={
        'TEMP': 'TEMP_mean_year',
        'PRCP': 'PRCP_total_year',
        'HEATWAVE_DAY': 'HEATWAVE_COUNT',
        'HEAVY_RAIN_DAY': 'HEAVY_RAIN_COUNT'})

    return yearly

def create_variability_df(df: pd.DataFrame) -> pd.DataFrame:
    var_df = (
        df.groupby('CITY', as_index=False)
        .agg({
            'TEMP': 'std',
            'PRCP': 'std'
        })
        .rename(columns={
            'TEMP': 'TEMP_std',
            'PRCP': 'PRCP_std'}))
    return var_df


def add_rolling(monthly_df: pd.DataFrame) -> pd.DataFrame:
    monthly_df = monthly_df.sort_values(['CITY', 'YEAR', 'MONTH'])

    monthly_df['TEMP_rolling_3'] = (
        monthly_df.groupby('CITY')['TEMP_mean']
        .transform(lambda x: x.rolling(3, min_periods=1).mean()))

    return monthly_df


def plot_seasonal_cycle(monthly_df):
    df = (
        monthly_df.groupby(['CITY', 'MONTH'], as_index=False)['TEMP_mean']
        .mean()
        .sort_values('MONTH')
    )

    fig = px.line(
        df, x='MONTH', y='TEMP_mean',
        color='CITY',
        color_discrete_map=CITY_COLORS,
        markers=True,
        title='Seasonal Temperature Cycle'
    )
    fig.update_layout(xaxis=dict(dtick=1))
    fig.show()

def plot_precip_cycle(monthly_df):
    df = (
        monthly_df.groupby(['CITY', 'MONTH'], as_index=False)['PRCP_sum']
        .mean()
        .sort_values('MONTH')
    )

    fig = px.line(
        df, x='MONTH', y='PRCP_sum',
        color='CITY',
        color_discrete_map=CITY_COLORS,
        markers=True,
        title='Seasonal Rainfall Cycle'
    )
    fig.update_layout(xaxis=dict(dtick=1))
    fig.show()

def plot_yearly_trend(yearly_df):
    df = yearly_df.sort_values('YEAR')

    fig = px.line(
        df,
        x='YEAR',
        y='TEMP_mean_year',
        color='CITY',
        color_discrete_map=CITY_COLORS,
        markers=True,
        title='Inter-Annual Temperature Trend'
    )
    fig.show()

def plot_all_heatmaps(monthly_df):
    cities = monthly_df['CITY'].unique()

    for city in cities:
        df = monthly_df[monthly_df['CITY'] == city].copy()

        # full grid (YEAR x MONTH)
        years = sorted(df['YEAR'].unique())
        months = list(range(1, 13))

        full_index = pd.MultiIndex.from_product(
            [years, months],
            names=['YEAR', 'MONTH']
        )

        df = df.set_index(['YEAR', 'MONTH']).reindex(full_index).reset_index()

        pivot = df.pivot(index='YEAR', columns='MONTH', values='TEMP_mean')
        pivot = pivot.sort_index().sort_index(axis=1)

        fig = px.imshow(
            pivot,
            aspect='auto',
            color_continuous_scale='RdYlBu_r',
            labels=dict(x="Month", y="Year", color="Temp (°C)"),
            title=f"{city} Temperature Heatmap"
        )

        fig.update_layout(
            xaxis=dict(tickmode='linear'),
            yaxis=dict(autorange='reversed')
        )

        fig.show()

def plot_variability(df):
    fig = px.box(
        df,
        x='CITY',
        y='TEMP',
        color='CITY',
        color_discrete_map=CITY_COLORS,
        title='Temperature Variability'
    )
    fig.show()

def plot_extreme_events(monthly_df):
    df = (
        monthly_df.groupby(['CITY', 'YEAR'], as_index=False)['HEATWAVE_COUNT']
        .sum()
        .sort_values('YEAR')
    )

    fig = px.line(
        df,
        x='YEAR',
        y='HEATWAVE_COUNT',
        color='CITY',
        color_discrete_map=CITY_COLORS,
        markers=True,
        title='Heatwave Trend'
    )
    fig.show()

def plot_rain_extremes(monthly_df):
    df = (
        monthly_df.groupby(['CITY', 'YEAR'], as_index=False)['EXTREME_RAIN_COUNT']
        .sum()
        .sort_values('YEAR')
    )

    fig = px.line(
        df,
        x='YEAR',
        y='EXTREME_RAIN_COUNT',
        color='CITY',
        color_discrete_map=CITY_COLORS,
        markers=True,
        title='Extreme Rainfall Trend'
    )
    fig.show()



def run_eda_pipeline(df: pd.DataFrame):
    df = prepare_analysis_df(df)
    monthly_df = create_monthly_df(df)
    yearly_df = create_yearly_df(df)
    var_df = create_variability_df(df)

    monthly_df = add_rolling(monthly_df)

    return df, monthly_df, yearly_df, var_df



if __name__ == "__main__":
    

    df = pd.concat([mumbai, delhi, dehradun, jodhpur], ignore_index=True)

    analysis_df, monthly_df, yearly_df, var_df = run_eda_pipeline(df)

    plot_seasonal_cycle(monthly_df)
    plot_precip_cycle(monthly_df)
    plot_yearly_trend(yearly_df)
    plot_all_heatmaps(monthly_df)
    plot_variability(analysis_df)
    plot_extreme_events(monthly_df)
    plot_rain_extremes(monthly_df)

