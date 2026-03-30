import os

from dash import Dash, Input, Output, dash_table, dcc, html
import pandas as pd
import plotly.express as px

from visualization import (
    CITY_COLORS,
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
)


def build_method_comparison(analysis: pd.DataFrame) -> pd.DataFrame:
    comparison_rows = []

    for city in sorted(analysis['CITY'].dropna().unique()):
        city_data = analysis[analysis['CITY'] == city].copy()
        temp_series = city_data['TEMP'].dropna()
        if temp_series.empty:
            continue

        original_std = temp_series.std()
        rolling_std = temp_series.rolling(window=30, center=True).mean().std()
        reduction = ((original_std - rolling_std) / original_std * 100) if original_std else 0.0

        comparison_rows.append({
            'City': city,
            'Original STD (C)': round(original_std, 2),
            'Rolling 30d STD (C)': round(rolling_std, 2),
            'Noise Reduction (%)': round(reduction, 1),
        })

    return pd.DataFrame(comparison_rows)


def load_dashboard_data():
    raw_df = load_all_saved_cleaned_data()
    analysis = prepare_analysis_df(raw_df)
    monthly = create_monthly_df(analysis)
    yearly = create_yearly_df(analysis)
    variability = create_variability_df(analysis)

    comparison_path = os.path.join(
        os.path.dirname(__file__),
        'Trend_analysis',
        'results',
        'method_comparison.csv',
    )
    comparison = pd.read_csv(comparison_path) if os.path.exists(comparison_path) else build_method_comparison(analysis)
    return analysis, monthly, yearly, variability, comparison


analysis_df, monthly_df, yearly_df, variability_df, comparison_df = load_dashboard_data()
available_cities = sorted(analysis_df['CITY'].dropna().unique().tolist())

PANEL_STYLE = {
    'backgroundColor': 'rgba(255,255,255,0.78)',
    'borderRadius': '24px',
    'boxShadow': '0 16px 40px rgba(20,35,45,0.10)',
    'backdropFilter': 'blur(6px)',
}

CARD_BASE_STYLE = {
    'padding': '18px',
    'borderRadius': '24px',
    'boxShadow': '0 16px 40px rgba(20,35,45,0.10)',
    'color': '#13212b',
}

GRAPH_STYLE = {**PANEL_STYLE, 'padding': '10px'}

app = Dash(__name__)
app.title = 'Weather Analysis Dashboard'

app.layout = html.Div(
    style={
        'minHeight': '100vh',
        'padding': '28px',
        'background': 'radial-gradient(circle at top left, #ffe2b8 0%, #f7efe3 30%, #d9e9f6 64%, #cadfc5 100%)',
        'fontFamily': 'Georgia, Cambria, Times New Roman, serif',
        'color': '#1f2a36',
    },
    children=[
        html.Div(
            style={'maxWidth': '1320px', 'margin': '0 auto'},
            children=[
                html.Div(
                    style={
                        'padding': '28px',
                        'marginBottom': '20px',
                        'borderRadius': '30px',
                        'background': 'linear-gradient(135deg, rgba(19,33,43,0.95), rgba(30,72,93,0.82))',
                        'boxShadow': '0 24px 54px rgba(20,30,40,0.20)',
                        'color': '#f8f3ea',
                    },
                    children=[
                        html.Div(
                            'Daily weather patterns from 2000 to 2024',
                            style={
                                'fontSize': '12px',
                                'textTransform': 'uppercase',
                                'letterSpacing': '1.8px',
                                'opacity': '0.78',
                                'marginBottom': '12px',
                            },
                        ),
                        html.H1(
                            'Weather Analysis Dashboard',
                            style={
                                'fontSize': '48px',
                                'lineHeight': '1.03',
                                'marginTop': '0',
                                'marginBottom': '12px',
                            },
                        ),
                        html.P(
                            'Explore how temperature, rainfall, variability, and extreme events behave across Mumbai, Delhi, Dehradun, and Jodhpur, then compare how well your smoothing methods reduce noise.',
                            style={
                                'fontSize': '18px',
                                'lineHeight': '1.55',
                                'maxWidth': '900px',
                                'margin': '0 0 18px 0',
                            },
                        ),
                        html.Div(
                            style={
                                'maxWidth': '420px',
                                'backgroundColor': 'rgba(255,255,255,0.10)',
                                'padding': '16px',
                                'borderRadius': '20px',
                            },
                            children=[
                                html.Label('City Filter', style={'display': 'block', 'fontWeight': 'bold', 'marginBottom': '8px'}),
                                dcc.Dropdown(
                                    id='city-filter',
                                    options=[{'label': city, 'value': city} for city in available_cities],
                                    value=available_cities,
                                    multi=True,
                                    placeholder='Select cities',
                                    style={'color': '#1f2a36'},
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    style={
                        'display': 'grid',
                        'gridTemplateColumns': 'repeat(4, minmax(0, 1fr))',
                        'gap': '16px',
                        'marginBottom': '18px',
                    },
                    children=[
                        html.Div(id='card-observations', style={**CARD_BASE_STYLE, 'background': 'linear-gradient(135deg, #fff3dd, #f2ddb0)'}),
                        html.Div(id='card-temp', style={**CARD_BASE_STYLE, 'background': 'linear-gradient(135deg, #ffd9a8, #f5b563)'}),
                        html.Div(id='card-rain', style={**CARD_BASE_STYLE, 'background': 'linear-gradient(135deg, #d6ebff, #9ccae7)'}),
                        html.Div(id='card-extremes', style={**CARD_BASE_STYLE, 'background': 'linear-gradient(135deg, #d8eed5, #a6d49d)'}),
                    ],
                ),
                html.Div(
                    style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '18px', 'marginBottom': '18px'},
                    children=[
                        dcc.Graph(id='seasonal-temp-chart', style=GRAPH_STYLE),
                        dcc.Graph(id='seasonal-rain-chart', style=GRAPH_STYLE),
                    ],
                ),
                html.Div(
                    style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '18px', 'marginBottom': '18px'},
                    children=[
                        dcc.Graph(id='yearly-trend-chart', style=GRAPH_STYLE),
                        dcc.Graph(id='variability-chart', style=GRAPH_STYLE),
                    ],
                ),
                html.Div(
                    style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '18px', 'marginBottom': '18px'},
                    children=[
                        dcc.Graph(id='heatwave-chart', style=GRAPH_STYLE),
                        dcc.Graph(id='rain-extreme-chart', style=GRAPH_STYLE),
                    ],
                ),
                html.Div(
                    style={'display': 'grid', 'gridTemplateColumns': '1.35fr 1fr', 'gap': '18px', 'marginBottom': '18px'},
                    children=[
                        dcc.Graph(id='heatmap-chart', style=GRAPH_STYLE),
                        dcc.Graph(id='method-bar-chart', style=GRAPH_STYLE),
                    ],
                ),
                html.Div(
                    style={**PANEL_STYLE, 'padding': '18px'},
                    children=[
                        html.H2('Trend Method Comparison', style={'marginTop': '0', 'marginBottom': '12px'}),
                        dash_table.DataTable(
                            id='comparison-table',
                            page_size=10,
                            style_table={'overflowX': 'auto'},
                            style_cell={
                                'padding': '10px',
                                'textAlign': 'left',
                                'fontFamily': 'Georgia, Cambria, Times New Roman, serif',
                                'backgroundColor': 'rgba(255,255,255,0.4)',
                            },
                            style_header={'fontWeight': 'bold', 'backgroundColor': '#e8dcc9'},
                        ),
                    ],
                ),
            ],
        )
    ],
)


def add_dashboard_theme(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(255,255,255,0)',
        font={'family': 'Georgia, Cambria, Times New Roman, serif', 'color': '#1f2a36'},
        title={'x': 0.03},
        margin={'l': 52, 'r': 28, 't': 72, 'b': 48},
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': 1.02, 'xanchor': 'left', 'x': 0},
    )
    return fig


def empty_figure(title):
    fig = px.scatter(title=title)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.add_annotation(
        text='Select at least one city to view this chart.',
        showarrow=False,
        x=0.5,
        y=0.5,
        xref='paper',
        yref='paper',
        font={'size': 16},
    )
    return add_dashboard_theme(fig)


def metric_card(title, value, subtitle):
    return [
        html.Div(title, style={'fontWeight': 'bold', 'fontSize': '15px', 'marginBottom': '8px'}),
        html.Div(value, style={'fontSize': '34px', 'fontWeight': 'bold', 'lineHeight': '1.1'}),
        html.Div(subtitle, style={'marginTop': '8px', 'fontSize': '13px', 'opacity': '0.72'}),
    ]


def method_comparison_bar(filtered_comparison):
    if filtered_comparison.empty:
        return empty_figure('Noise Reduction by City')

    fig = px.bar(
        filtered_comparison,
        x='City',
        y='Noise Reduction (%)',
        color='City',
        color_discrete_map=CITY_COLORS,
        text='Noise Reduction (%)',
        title='30-Day Rolling Window Noise Reduction',
    )
    fig.update_traces(textposition='outside')
    fig.update_yaxes(title='Noise Reduction (%)')
    return add_dashboard_theme(fig)


@app.callback(
    Output('card-observations', 'children'),
    Output('card-temp', 'children'),
    Output('card-rain', 'children'),
    Output('card-extremes', 'children'),
    Output('seasonal-temp-chart', 'figure'),
    Output('seasonal-rain-chart', 'figure'),
    Output('yearly-trend-chart', 'figure'),
    Output('variability-chart', 'figure'),
    Output('heatwave-chart', 'figure'),
    Output('rain-extreme-chart', 'figure'),
    Output('heatmap-chart', 'figure'),
    Output('method-bar-chart', 'figure'),
    Output('comparison-table', 'data'),
    Output('comparison-table', 'columns'),
    Input('city-filter', 'value'),
)
def update_dashboard(selected_cities):
    if not selected_cities:
        return (
            metric_card('Observations', '0', 'No cities selected'),
            metric_card('Average Temperature', 'N/A', 'Select a city'),
            metric_card('Average Rainfall', 'N/A', 'Select a city'),
            metric_card('Extreme Days', 'N/A', 'Select a city'),
            empty_figure('Seasonal Temperature Cycle'),
            empty_figure('Seasonal Rainfall Cycle'),
            empty_figure('Inter-Annual Temperature Trend'),
            empty_figure('Temperature Variability'),
            empty_figure('Heatwave Trend'),
            empty_figure('Extreme Rainfall Trend'),
            empty_figure('Monthly Temperature Heatmap'),
            empty_figure('Noise Reduction by City'),
            comparison_df.to_dict('records') if not comparison_df.empty else [],
            [{'name': col, 'id': col} for col in comparison_df.columns],
        )

    filtered_analysis = analysis_df[analysis_df['CITY'].isin(selected_cities)].copy()
    filtered_monthly = monthly_df[monthly_df['CITY'].isin(selected_cities)].copy()
    filtered_yearly = yearly_df[yearly_df['CITY'].isin(selected_cities)].copy()
    filtered_comparison = comparison_df[comparison_df['City'].isin(selected_cities)].copy() if not comparison_df.empty else comparison_df

    heatwave_days = int(filtered_analysis['HEATWAVE_DAY'].fillna(0).sum()) if 'HEATWAVE_DAY' in filtered_analysis.columns else 0
    heavy_rain_days = int(filtered_analysis['HEAVY_RAIN_DAY'].fillna(0).sum()) if 'HEAVY_RAIN_DAY' in filtered_analysis.columns else 0
    extreme_total = heatwave_days + heavy_rain_days

    seasonal_temp_fig = add_dashboard_theme(plot_seasonal_cycle(filtered_monthly))
    seasonal_rain_fig = add_dashboard_theme(plot_precip_cycle(filtered_monthly))
    yearly_trend_fig = add_dashboard_theme(plot_yearly_trend(filtered_yearly))
    variability_fig = add_dashboard_theme(plot_variability(filtered_analysis))
    heatwave_fig = add_dashboard_theme(plot_extreme_events(filtered_monthly))
    rain_extreme_fig = add_dashboard_theme(plot_rain_extremes(filtered_monthly))
    heatmap_fig = add_dashboard_theme(plot_all_heatmaps(filtered_monthly))
    method_bar_fig = method_comparison_bar(filtered_comparison)

    return (
        metric_card('Observations', f'{len(filtered_analysis):,}', 'Rows in the filtered daily dataset'),
        metric_card('Average Temperature', f"{filtered_analysis['TEMP'].mean():.2f} C", 'Across all selected cities and dates'),
        metric_card('Average Rainfall', f"{filtered_analysis['PRCP'].mean():.2f} mm", 'Daily precipitation mean'),
        metric_card('Extreme Days', f'{extreme_total:,}', f'Heatwave + heavy rain flags: {heatwave_days:,} + {heavy_rain_days:,}'),
        seasonal_temp_fig,
        seasonal_rain_fig,
        yearly_trend_fig,
        variability_fig,
        heatwave_fig,
        rain_extreme_fig,
        heatmap_fig,
        method_bar_fig,
        filtered_comparison.to_dict('records') if not filtered_comparison.empty else [],
        [{'name': col, 'id': col} for col in filtered_comparison.columns],
    )


if __name__ == '__main__':
    app.run(debug=True)
