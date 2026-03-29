import sys
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CLEANED_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'cleaned_data', 'nc_cleaned')
)


def load_saved_cleaned_city(filename: str, city_name: str) -> pd.DataFrame:
    path = os.path.join(CLEANED_DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f'Saved cleaned file not found: {path}')

    try:
        import xarray as xr
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            'xarray is required to load saved .nc cleaned files. Install it with: pip install xarray'
        ) from exc

    with xr.open_dataset(path) as ds:
        df = ds.to_dataframe().reset_index()

    df = normalize_analysis_schema(df, city_name)
    return df


def normalize_analysis_schema(df: pd.DataFrame, city_name: str) -> pd.DataFrame:
    df = df.copy()

    rename_map = {
        'TEMP_C': 'TEMP',
        'DEWP_C': 'DEWP',
        'PRCP_MM': 'PRCP',
        'WDSP_MS': 'WDSP',
        'MAX_C': 'MAX',
        'MIN_C': 'MIN',
    }
    existing_renames = {old: new for old, new in rename_map.items() if old in df.columns}
    df = df.rename(columns=existing_renames)

    if 'CITY' not in df.columns:
        df['CITY'] = city_name
    else:
        df['CITY'] = df['CITY'].fillna(city_name)

    if 'SEASON' not in df.columns and 'MONTH' in df.columns:
        season_map = {
            12: 'Winter', 1: 'Winter', 2: 'Winter',
            3: 'Pre-Monsoon', 4: 'Pre-Monsoon', 5: 'Pre-Monsoon',
            6: 'Monsoon', 7: 'Monsoon', 8: 'Monsoon', 9: 'Monsoon',
            10: 'Post-Monsoon', 11: 'Post-Monsoon',
        }
        df['SEASON'] = df['MONTH'].map(season_map)

    for col in ['HEATWAVE_DAY', 'HEAVY_RAIN_DAY', 'VERY_HEAVY_RAIN_DAY', 'EXTREME_RAIN_DAY']:
        if col not in df.columns:
            df[col] = 0

    return df


CITY_COLORS = {
    'Mumbai': '#1f77b4',
    'Delhi': '#d62728',
    'Dehradun': '#2ca02c',
    'Jodhpur': '#E06C06',
}


def prepare_analysis_df(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'CITY', 'YEAR', 'MONTH', 'SEASON',
        'TEMP', 'DEWP', 'PRCP', 'WDSP', 'MAX', 'MIN',
        'HEATWAVE_DAY', 'HEAVY_RAIN_DAY',
        'VERY_HEAVY_RAIN_DAY', 'EXTREME_RAIN_DAY'
    ]
    cols = [c for c in cols if c in df.columns]

    df = df[cols].copy()
    if 'MAX' in df.columns and 'MIN' in df.columns:
        df['TEMP_RANGE'] = df['MAX'] - df['MIN']
    return df


def create_monthly_df(df: pd.DataFrame) -> pd.DataFrame:
    agg_map = {
        'TEMP': 'mean',
        'DEWP': 'mean',
        'WDSP': 'mean',
        'PRCP': 'sum',
        'MAX': 'mean',
        'MIN': 'mean',
        'HEATWAVE_DAY': 'sum',
        'HEAVY_RAIN_DAY': 'sum',
        'VERY_HEAVY_RAIN_DAY': 'sum',
        'EXTREME_RAIN_DAY': 'sum'
    }
    agg_map = {key: value for key, value in agg_map.items() if key in df.columns}

    monthly = df.groupby(['CITY', 'YEAR', 'MONTH'], as_index=False).agg(agg_map)

    rename_map = {
        'TEMP': 'TEMP_mean',
        'PRCP': 'PRCP_sum',
        'HEATWAVE_DAY': 'HEATWAVE_COUNT',
        'HEAVY_RAIN_DAY': 'HEAVY_RAIN_COUNT',
        'VERY_HEAVY_RAIN_DAY': 'VERY_HEAVY_RAIN_COUNT',
        'EXTREME_RAIN_DAY': 'EXTREME_RAIN_COUNT'
    }
    monthly = monthly.rename(columns={k: v for k, v in rename_map.items() if k in monthly.columns})

    return monthly


def create_yearly_df(df: pd.DataFrame) -> pd.DataFrame:
    agg_map = {
        'TEMP': 'mean',
        'PRCP': 'sum',
        'MAX': 'max',
        'MIN': 'min',
        'HEATWAVE_DAY': 'sum',
        'HEAVY_RAIN_DAY': 'sum'
    }
    agg_map = {key: value for key, value in agg_map.items() if key in df.columns}

    yearly = df.groupby(['CITY', 'YEAR'], as_index=False).agg(agg_map)

    rename_map = {
        'TEMP': 'TEMP_mean_year',
        'PRCP': 'PRCP_total_year',
        'HEATWAVE_DAY': 'HEATWAVE_COUNT',
        'HEAVY_RAIN_DAY': 'HEAVY_RAIN_COUNT'
    }
    yearly = yearly.rename(columns={k: v for k, v in rename_map.items() if k in yearly.columns})

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
            'PRCP': 'PRCP_std'
        })
    )
    return var_df


def add_rolling(monthly_df: pd.DataFrame) -> pd.DataFrame:
    monthly_df = monthly_df.sort_values(['CITY', 'YEAR', 'MONTH'])

    monthly_df['TEMP_rolling_3'] = (
        monthly_df.groupby('CITY')['TEMP_mean']
        .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )

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

<<<<<<< HEAD

def plot_all_heatmaps(monthly_df):
    cities = monthly_df['CITY'].unique()
    if len(cities) == 0:
        return

    months = list(range(1, 13))
    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    fig = go.Figure()

    for idx, city in enumerate(cities):
        df = monthly_df[monthly_df['CITY'] == city].copy()
        years = sorted(df['YEAR'].unique())
=======
def plot_all_heatmaps(monthly_df):
    cities = monthly_df['CITY'].unique()

    for city in cities:
        df = monthly_df[monthly_df['CITY'] == city].copy()

        # full grid (YEAR x MONTH)
        years = sorted(df['YEAR'].unique())
        months = list(range(1, 13))
>>>>>>> aa3595fe3d59a0746211190ea3e71e019c5edd31

        full_index = pd.MultiIndex.from_product(
            [years, months],
            names=['YEAR', 'MONTH']
        )

        df = df.set_index(['YEAR', 'MONTH']).reindex(full_index).reset_index()
<<<<<<< HEAD
        pivot = df.pivot(index='YEAR', columns='MONTH', values='TEMP_mean')
        pivot = pivot.reindex(columns=months).sort_index()

        fig.add_trace(go.Heatmap(
            z=pivot.values,
            x=month_labels,
            y=pivot.index.tolist(),
            colorscale='RdYlBu_r',
            colorbar=dict(title='Temp (C)'),
            visible=(idx == 0),
            hovertemplate=(
                f'City: {city}<br>'
                'Year: %{y}<br>'
                'Month: %{x}<br>'
                'Temp: %{z:.2f} C<extra></extra>'
            )
        ))

    buttons = []
    for idx, city in enumerate(cities):
        visible = [False] * len(cities)
        visible[idx] = True
        buttons.append({
            'label': city,
            'method': 'update',
            'args': [
                {'visible': visible},
                {'title': f'{city} Temperature Heatmap'}
            ]
        })

    fig.update_layout(
        title=f'{cities[0]} Temperature Heatmap',
        updatemenus=[{
            'buttons': buttons,
            'direction': 'down',
            'showactive': True,
            'x': 1.02,
            'xanchor': 'left',
            'y': 1.0,
            'yanchor': 'top',
        }],
        xaxis=dict(title='Month'),
        yaxis=dict(title='Year', autorange='reversed'),
        margin=dict(r=160)
    )
=======

        pivot = df.pivot(index='YEAR', columns='MONTH', values='TEMP_mean')
        pivot = pivot.sort_index().sort_index(axis=1)

        fig = px.imshow(
            pivot,
            aspect='auto',
            color_continuous_scale='RdYlBu_r',
            labels=dict(x="Month", y="Year", color="Temp (°C)"),
            title=f"{city} Temperature Heatmap"
        )
>>>>>>> aa3595fe3d59a0746211190ea3e71e019c5edd31

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
    if 'HEATWAVE_COUNT' not in monthly_df.columns:
        return

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
    if 'EXTREME_RAIN_COUNT' not in monthly_df.columns:
        return

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
    mumbai = load_saved_cleaned_city('mumbai_cleaned.nc', 'Mumbai')
    delhi = load_saved_cleaned_city('delhi_cleaned.nc', 'Delhi')
    dehradun = load_saved_cleaned_city('dehradun_cleaned.nc', 'Dehradun')
    jodhpur = load_saved_cleaned_city('jodhpur_cleaned.nc', 'Jodhpur')

    df = pd.concat([mumbai, delhi, dehradun, jodhpur], ignore_index=True)

    analysis_df, monthly_df, yearly_df, var_df = run_eda_pipeline(df)

<<<<<<< HEAD
    # You can uncomment the plots you want to visualize
    #plot_seasonal_cycle(monthly_df)
    #plot_precip_cycle(monthly_df)
    #plot_yearly_trend(yearly_df)
    #plot_all_heatmaps(monthly_df)
    #plot_variability(analysis_df)
    #plot_extreme_events(monthly_df)
    #plot_rain_extremes(monthly_df)
=======
    plot_seasonal_cycle(monthly_df)
    plot_precip_cycle(monthly_df)
    plot_yearly_trend(yearly_df)
    plot_all_heatmaps(monthly_df)
    plot_variability(analysis_df)
    plot_extreme_events(monthly_df)
    plot_rain_extremes(monthly_df)

>>>>>>> aa3595fe3d59a0746211190ea3e71e019c5edd31
