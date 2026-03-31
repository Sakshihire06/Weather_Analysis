import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

from raw_data.mumbai_raw   import get_raw_data as get_mumbai_raw
from raw_data.delhi_raw    import get_raw_data as get_delhi_raw
from raw_data.dehradun_raw import get_raw_data as get_dehradun_raw
from raw_data.jodhpur_raw  import get_raw_data as get_jodhpur_raw
from cleaned_data.mumbai_cleaned   import get_cleaned_data as get_mumbai
from cleaned_data.delhi_cleaned    import get_cleaned_data as get_delhi
from cleaned_data.dehradun_cleaned import get_cleaned_data as get_dehradun
from cleaned_data.jodhpur_cleaned  import get_cleaned_data as get_jodhpur

mumbai_raw   = get_mumbai_raw()
delhi_raw    = get_delhi_raw()
dehradun_raw = get_dehradun_raw()
jodhpur_raw  = get_jodhpur_raw()
mumbai   = get_mumbai()
delhi    = get_delhi()
dehradun = get_dehradun()
jodhpur  = get_jodhpur()

raw     = {'Mumbai': mumbai_raw, 'Delhi': delhi_raw, 'Dehradun': dehradun_raw, 'Jodhpur': jodhpur_raw}
cleaned = {'Mumbai': mumbai,     'Delhi': delhi,     'Dehradun': dehradun,     'Jodhpur': jodhpur}

cities       = ['Mumbai', 'Delhi', 'Dehradun', 'Jodhpur']
years        = list(range(2000, 2025))
stat_vars    = ['TEMP', 'MAX', 'MIN', 'PRCP']
anomaly_cols = ['TEMP_anomaly', 'MAX_anomaly', 'MIN_anomaly', 'PRCP_anomaly', 'WDSP_anomaly', 'DEWP_anomaly']
colors       = {'Mumbai': '#2196F3', 'Delhi': '#F44336', 'Dehradun': '#4CAF50', 'Jodhpur': '#FF9800'}

# noaa uses these placeholder values when data is not recorded
# we treat them as missing
noaa_fill = {
    'TEMP': 9999.9, 'DEWP': 9999.9, 'SLP': 9999.9, 'STP': 9999.9,
    'VISIB': 999.9, 'WDSP': 999.9,  'MXSPD': 999.9, 'GUST': 999.9,
    'MAX': 9999.9,  'MIN': 9999.9,   'PRCP': 99.99,
}
all_vars = list(noaa_fill.keys())

sns.set_theme(style='whitegrid')

# ── figure 1: how much data is missing per variable per year ──────────────
fig1, axes = plt.subplots(2, 2, figsize=(20, 12))
fig1.suptitle('Data Quality Report — How Much Data is Missing per Year (raw data)',
              fontsize=14, fontweight='bold')

for idx, city in enumerate(cities):
    ax = axes[idx // 2][idx % 2]
    df = raw[city].copy()
    df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
    df['YEAR'] = df['DATE'].dt.year

    # for each variable, check what % of values are the fill value or just empty
    matrix = pd.DataFrame(index=all_vars, columns=years, dtype=float)
    for var, fill_val in noaa_fill.items():
        if var in df.columns:
            for yr in years:
                yr_df = df[df['YEAR'] == yr]
                if len(yr_df) == 0:
                    matrix.loc[var, yr] = 100.0
                else:
                    missing_pct = ((yr_df[var] == fill_val) | yr_df[var].isna()).mean() * 100
                    matrix.loc[var, yr] = round(missing_pct, 1)
        else:
            matrix.loc[var, :] = 100.0

    sns.heatmap(matrix.astype(float), ax=ax, cmap='YlOrRd', vmin=0, vmax=100,
                linewidths=0.3, cbar_kws={'label': '% Missing'}, xticklabels=4)
    ax.set_title(city, fontsize=13, fontweight='bold', color=colors[city])
    ax.set_xlabel('Year')
    ax.set_ylabel('Variable')
    ax.tick_params(axis='x', rotation=45, labelsize=8)
    ax.tick_params(axis='y', rotation=0, labelsize=9)

fig1.tight_layout(rect=[0, 0, 1, 0.95])
fig1.savefig('data_quality_missing.png', dpi=150, bbox_inches='tight')

# ── figure 2: coverage, anomalies, stats, fill value counts ───────────────
fig2, axes2 = plt.subplots(2, 2, figsize=(20, 14))
fig2.suptitle('Data Quality Report — Coverage, Anomalies & Statistics',
              fontsize=14, fontweight='bold')

# how many days were recorded each year
ax_cov = axes2[0][0]
for city in cities:
    df = raw[city].copy()
    df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
    df['YEAR'] = df['DATE'].dt.year
    days_per_year = df.groupby('YEAR').size().reindex(years, fill_value=0)
    ax_cov.plot(years, days_per_year, marker='o', markersize=3, label=city, color=colors[city])
ax_cov.axhline(365, color='black', linestyle='--', linewidth=0.8, label='expected (365)')
ax_cov.set_title('Days Recorded per Year (raw data)', fontsize=12, fontweight='bold')
ax_cov.set_ylabel('Days recorded')
ax_cov.set_xlabel('Year')
ax_cov.legend(fontsize=9)
ax_cov.tick_params(axis='x', rotation=45)

# how many unusual values were flagged per variable per city
ax_ano = axes2[0][1]
labels = [c.replace('_anomaly', '') for c in anomaly_cols if c in list(cleaned.values())[0].columns]
x      = np.arange(len(labels))
width  = 0.18
for i, city in enumerate(cities):
    df     = cleaned[city]
    counts = [int(df[c].sum()) for c in anomaly_cols if c in df.columns]
    ax_ano.bar(x + i * width, counts, width=width, label=city, color=colors[city], edgecolor='white')
ax_ano.set_title('Unusual Values Flagged per Variable per City', fontsize=12, fontweight='bold')
ax_ano.set_ylabel('Count')
ax_ano.set_xticks(x + width * 1.5)
ax_ano.set_xticklabels(labels)
ax_ano.legend(fontsize=9)

# basic stats for key weather variables
ax_tbl = axes2[1][0]
ax_tbl.axis('off')
rows = []
for city in cities:
    df = cleaned[city]
    for var in stat_vars:
        if var in df.columns:
            s = df[var].dropna()
            rows.append([city, var, f'{s.mean():.1f}', f'{s.std():.1f}',
                         f'{s.min():.1f}', f'{s.max():.1f}', f'{s.median():.1f}'])
tbl_df = pd.DataFrame(rows, columns=['City', 'Var', 'Mean', 'Std', 'Min', 'Max', 'Median'])
tbl    = ax_tbl.table(cellText=tbl_df.values, colLabels=tbl_df.columns,
                      loc='center', cellLoc='center')
tbl.auto_set_font_size(False)
tbl.set_fontsize(9)
tbl.scale(1.2, 1.5)
for j in range(len(tbl_df.columns)):
    tbl[0, j].set_facecolor('#37474F')
    tbl[0, j].set_text_props(color='white', fontweight='bold')
city_light = {'Mumbai': '#BBDEFB', 'Delhi': '#FFCDD2', 'Dehradun': '#C8E6C9', 'Jodhpur': '#FFE0B2'}
for i, row in enumerate(rows):
    for j in range(len(tbl_df.columns)):
        tbl[i + 1, j].set_facecolor(city_light[row[0]])
ax_tbl.set_title('Basic Stats for Key Variables (cleaned data)', fontsize=12, fontweight='bold', pad=10)

# how many fill values were found and replaced with NaN during cleaning
ax_out = axes2[1][1]
fill_counts = {}
for city in cities:
    df = raw[city]
    per_var = {}
    for var, fill_val in noaa_fill.items():
        if var in df.columns:
            per_var[var] = int((df[var] == fill_val).sum())
    fill_counts[city] = per_var

fill_df = pd.DataFrame(fill_counts).T.fillna(0)
fill_df = fill_df[fill_df.sum().sort_values(ascending=False).index]
fill_df.plot(kind='bar', ax=ax_out, colormap='tab10', edgecolor='white', width=0.65)

for bar in ax_out.patches:
    if bar.get_height() > 0:
        ax_out.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 10,
                    str(int(bar.get_height())), ha='center', va='bottom', fontsize=6)

ax_out.set_title('Fill Values Found and Replaced per City (raw data)', fontsize=12, fontweight='bold')
ax_out.set_ylabel('Count')
ax_out.set_xlabel('')
ax_out.tick_params(axis='x', rotation=0)
ax_out.legend(title='Variable', fontsize=8, bbox_to_anchor=(1.01, 1), loc='upper left')

fig2.tight_layout(rect=[0, 0, 1, 0.95])
fig2.savefig('data_quality_stats.png', dpi=150, bbox_inches='tight')

plt.show()
print('done')