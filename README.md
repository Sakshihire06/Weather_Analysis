# Weather Analysis

Weather Analysis is a Python project for studying long-term daily weather patterns across four Indian cities:

- Mumbai
- Delhi
- Dehradun
- Jodhpur

The project covers the full workflow from raw NOAA GSOD station data to cleaned local datasets, exploratory analysis, trend analysis, and an interactive dashboard.

## Current Project Status

The repo currently includes:

- raw data loaders for all four cities
- cleaned-data pipelines with metric-unit conversion and anomaly handling
- exploratory analysis utilities in `visualization/`
- trend-analysis scripts for rolling average, STL decomposition, harmonic analysis, and method comparison
- a Dash dashboard under `dashboard/app.py` with a root `app.py` launcher
- local `.nc` datasets in `raw_data/nc_raw/` and `cleaned_data/nc_cleaned/`

The dashboard and analysis scripts now work from the local saved datasets, so they do not depend on live NOAA downloads every time you run them.

## Repo Structure

```text
Weather_Analysis/
|-- app.py
|-- dashboard/
|   `-- app.py
|-- requirements.txt
|-- raw_data/
|-- cleaned_data/
|-- Exploratory_Analysis/
|-- Refinement/
|-- Trend_analysis/
|-- visualization/
|-- data_preprocessing/
`-- Smoothening_data/
```

## Main Components

### 1. Raw Data

Files in `raw_data/` load city-level GSOD weather data. The repo also contains saved NetCDF versions under `raw_data/nc_raw/`, which are used as the first local source when available.

### 2. Cleaned Data

Files in `cleaned_data/` clean and standardize the data by:

- parsing dates
- converting imperial units to metric units
- replacing NOAA missing-value sentinels with `NaN`
- removing physically impossible values
- preserving known extreme events
- applying month-aware anomaly filtering

The cleaned NetCDF datasets are stored in `cleaned_data/nc_cleaned/`.

### 3. Exploratory Analysis

The repo now includes exploratory analysis scripts under `Exploratory_Analysis/` and reusable chart helpers under `visualization/`.

These cover:

- seasonal temperature cycles
- rainfall cycles
- yearly temperature trends
- variability plots
- heatmaps
- heatwave and rainfall-extreme summaries

### 4. Trend Analysis

The `Trend_analysis/` folder now centers on `trend_analysis.py`, which runs:

- rolling-window smoothing
- STL trend-seasonal-residual decomposition
- Fourier-based harmonic analysis
- method comparison across smoothing approaches

These scripts write outputs to `Trend_analysis/results/` when run locally.

### 5. Refinement

The `Refinement/` folder contains:

- `1_smoothing_refinement.py`
- `2_anomaly_threshold_refinement.py`
- `3_extreme_event_refinement.py`
- result tables under `Refinement/results/`

### 5. Dashboard

The dashboard logic lives in `dashboard/app.py`, and the root `app.py` is a small launcher for convenience.

The dashboard presents:

- summary metric cards
- seasonal temperature and rainfall charts
- yearly temperature trend
- variability analysis
- heatwave and extreme-rain views
- a temperature heatmap
- trend-method comparison table and bar chart

## Installation

Create or activate a Python environment, then install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Running the Dashboard

From the project root, you can run either:

```powershell
python app.py
```

or:

```powershell
python dashboard/app.py
```

Dash will print a local URL, usually:

```text
http://127.0.0.1:8050/
```

Open that URL in your browser.

## Running Trend Analysis Scripts

You can run the main trend-analysis script from the project root:

```powershell
python Trend_analysis/trend_analysis.py
```

## Key Dependencies

- `dash`
- `plotly`
- `pandas`
- `xarray`
- `statsmodels`
- `numpy`
- `matplotlib`
- `scipy`

## Notes

- The dashboard reads current outputs from `reports/`, `Trend_analysis/results/`, and `Refinement/results/`.
- The root `app.py` is a compatibility launcher; the main dashboard source is `dashboard/app.py`.
