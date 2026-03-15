# Weather_Analysis
## What This Project Is About

This is a Python-based data analysis project that looks at daily weather patterns across four Indian cities — Mumbai, Delhi, Dehradun, and Jaipur — over the last 25 years. The data is taken from NOAA's Global Summary of the Day (GSOD) database, which is a publicly available source that records daily weather observations from stations all around the world.

The main idea was to go from raw downloaded data all the way to clean, analysis-ready data, and then explore what the numbers actually say about how weather behaves differently across these cities over time.



## Part 1 — Getting the Data

The data was downloaded directly from NOAA's website using Python, so there is no manual step involved. Each city has a unique station ID, and for each year from 2000 to 2024, there is a separate CSV file available at a URL like:

```
https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/{year}/{station_id}.csv
```

All 25 files per city are downloaded in a loop and combined into one dataframe. The four station IDs used are Mumbai (43003099999), Delhi (42182099999), Dehradun (42189099999), and Jaipur (42170099999). Jaipur had coverage gaps in some early years, so the script automatically tests a few backup station IDs and picks whichever one has confirmed data.

One problem I ran into early was that NOAA's server kept returning HTTP 503 errors when using the default `pd.read_csv(url)` method. This was happening because NOAA's CDN treats plain Python requests as bots and blocks them. The fix was to use a `requests.Session` with proper browser-like headers (a Chrome User-Agent, Accept-Language, and Referer), along with retry logic that waits and tries again if a 503 comes back. I also added a small random delay between requests so it doesn't look like automated scraping. After these changes the downloads worked consistently.

To speed things up, I also used Python's `ThreadPoolExecutor` to download 3 years simultaneously instead of one by one, which cut the total download time down a lot.



## Part 2 — Cleaning the Data

This was probably the most important and careful part of the project. Raw GSOD data comes with several issues that need to be handled before any analysis can be done.

**Unit conversion.** NOAA stores everything in imperial units — temperatures in Fahrenheit, precipitation in inches, and wind speed in knots. All of these were converted to metric (°C, mm, and m/s) as a first step since the analysis and comparisons are done in standard units.

**Missing value codes.** NOAA does not use NaN for missing data. Instead it uses specific fill values like 9999.9 for temperature and 99.99 for precipitation. These had to be identified and replaced with actual NaN before doing anything else, because otherwise they appear as real observations and break all the statistics.

**Duplicates.** Some station records had more than one row for the same date. These were removed by keeping only the first occurrence.

**Impossible values.** After unit conversion, a physical plausibility check was applied to catch values that simply cannot exist in the real world, regardless of how extreme the weather was. There are several kinds of these. Temperature readings above 60°C or below -90°C go beyond the absolute records ever measured anywhere on Earth, so anything outside that range is a sensor or transcription error. Negative rainfall is impossible since rain cannot be a negative quantity, and the same applies to wind speed — negative wind values usually come from how older station software encoded certain error states. Rainfall that somehow exceeds 2000mm in a single day also gets removed, since even the highest ever recorded single-day rainfall in the world was around 1825mm. After converting from Fahrenheit, some temperatures that were already close to the sentinel fill value of 9999.9°F end up producing wildly large Celsius values, and these are caught here too. The maximum temperature for a day must always be greater than or equal to the minimum temperature — if MAX comes out lower than MIN after conversion, that is a recording error and both values are removed. Similarly, dew point temperature physically cannot be higher than the actual air temperature, so any row where that happens is also flagged. All of these impossible values are set to NaN rather than being corrected, since there is no reliable way to know what the actual reading should have been.

**The outlier problem — and why not all unusual values are errors.** This is the part I thought about most carefully. A lot of standard data cleaning approaches will flag statistical outliers and remove them. But in weather data, that is actually the wrong thing to do. A day with 900mm of rainfall is not a bad data point — it is the 2005 Mumbai floods, one of the most severe urban flood events in Indian history. Removing it because it looks statistically unusual would mean losing exactly the kind of event this project is meant to study.

To handle this properly, the cleaning pipeline separates all unusual values into three distinct categories, and each category is treated differently.

The first category is instrument and recording errors. These are values that are physically impossible — they could never happen in the real world under any circumstances. Examples include negative rainfall, temperatures beyond Earth's absolute extremes, or a day where the maximum temperature is lower than the minimum. These are deleted from the dataset because they carry no real information. This is the only category where data is actually removed.

The second category is real extreme weather events. These are values that look unusual but are completely real — they just represent genuinely severe weather. A 45°C day in Delhi during a heatwave, or 300mm of rain in Mumbai during a bad monsoon day, these are not errors. They are kept in the dataset exactly as they are, but they get labelled with boolean flag columns so that downstream analysis can identify them. The labels follow India Meteorological Department (IMD) standard thresholds — for example, any day above 64.5mm of rainfall is flagged as a Heavy Rain day, and any day above 40°C maximum temperature is flagged as a Heatwave day. Some specific historical events like the Uttarakhand 2013 cloudburst and the 2022 Delhi heatwave are also manually marked in the code so they can never be accidentally treated as errors by any automated step.

The third category is statistical anomalies. These are values that are not impossible, not a known extreme event, but are still unusually far from what is typical for that variable in that month. To measure this, a robust z-score is computed using the median and MAD (Median Absolute Deviation) instead of the usual mean and standard deviation. The reason for this choice is important: if you use the regular mean and SD, a real extreme event inflates both of them, which paradoxically makes the event look less unusual than it actually is — the very thing you are trying to detect. The median and MAD are not affected by extreme values in the same way. Any observation with a robust z-score above 3.5 gets flagged as a statistical anomaly, but like extreme events, it stays in the dataset. The flag just tells future analysis to take note of it.

After all of this, each city ends up with roughly 8,900 to 9,125 clean rows. The final dataset includes the original weather variables converted to metric units, along with new columns for season, IMD event flags, robust z-scores, and monthly percentile ranks.


## Part 3 — Data Quality Report

After cleaning, a quality assessment was done across all four cities to understand how reliable and consistent each city's data is. This is important because two cities might have the same number of rows on paper, but one might have far more missing values or a shorter stretch of usable records than the other, which affects how much confidence you can place in any comparisons made between them.

**Record length and coverage.** All four cities have data from 2000 to 2024, giving a maximum possible record of around 9,125 daily observations each. In practice, Jaipur's records are slightly shorter because the primary NOAA station for Jaipur had gaps in some early years, requiring a fallback to a backup station ID. Delhi and Mumbai have the most complete records, while Dehradun has some years with noticeably fewer observations than expected, likely due to periods where the station was not reporting.

**Missing data patterns.** The rate of missing values is not the same across all variables or all cities. Temperature variables (TEMP, MAX, MIN) tend to be well recorded across all four cities since these are the most fundamental observations. Precipitation is the most commonly missing variable, particularly for Dehradun and Jaipur during non-monsoon months when dry days may not always be reported as zero — the distinction between "no rain" and "no observation" is not always clear in the raw data. Wind speed and dew point have higher missingness across the board, with some years where these columns are almost entirely absent for certain stations. The pipeline generates a month-by-month missing rate heatmap for each variable and each city so these patterns can be seen clearly.

**Measurement inconsistencies.** One pattern that shows up in Jaipur's data specifically is a period in the early 2000s where precipitation values appear to have been recorded in a different unit before conversion, producing a cluster of values that are plausible but systematically lower than surrounding years. This is flagged in the anomaly detection step. Mumbai's records are the most internally consistent, which likely reflects the fact that it is a major international airport station with more rigorous maintenance. Dehradun, being a smaller inland station, has occasional year-long stretches where wind speed readings are missing entirely and where temperature ranges are narrower than expected, suggesting the station may have had instrumentation issues during those periods.

**Overall quality ranking.** Based on record completeness, missing value rates, and internal consistency, Mumbai and Delhi have the highest quality data for this 25-year period. Dehradun is reliable for temperature and precipitation but less so for wind and dew point. Jaipur has the most caveats, particularly for the pre-2005 period, and any conclusions drawn from Jaipur's early data should be treated with more caution than the other three cities.

## Part 4 — Iterative Refinement

While the initial pipeline produced clean datasets and useful visualizations, exploratory analysis revealed a few areas where the methodology could be improved. Rather than treating the cleaning and analysis rules as fixed, several steps were refined after inspecting the behavior of the data across seasons and cities.

**Seasonal Refinement of Anomaly Detection**

The first version of the anomaly detection step used a robust z-score computed across the entire dataset for each variable. Although this approach is resistant to extreme values, applying a single global distribution to weather data introduced a seasonal bias. In particular, monsoon rainfall and summer heat events appeared statistically unusual when compared against the full-year distribution, even though they are normal within their seasonal context.

To address this, anomaly detection was recalculated within seasonal subsets of the data. Instead of computing the median and median absolute deviation over the full record, these statistics are now calculated within each calendar month. This allows rainfall during the monsoon and temperature during peak summer to be evaluated relative to their expected seasonal ranges rather than the annual distribution. The refinement reduces false anomaly flags while preserving genuinely unusual observations.

**Threshold Sensitivity Analysis**

The anomaly detection threshold was also evaluated through sensitivity testing. The original implementation used a robust z-score threshold of 3.5, which is commonly used for identifying extreme deviations. However, exploratory analysis showed that the number of flagged observations varied noticeably between cities and seasons.

To ensure that the anomaly detection step remained stable and interpretable, multiple thresholds were tested, including 3.0, 3.5, and 4.0. The results were compared by examining the number and distribution of flagged observations across cities and time periods. A threshold of 3.5 was retained because it provided a balanced detection rate: it preserved genuine extremes without producing an excessive number of statistical anomalies.

**Refinement of Temperature Gap Handling**

During visualization of rolling averages and trend estimates, short gaps in the temperature time series occasionally created small discontinuities in the smoothed curves. These gaps occurred when sensor errors or missing records had previously been converted to NaN during the cleaning stage.

To maintain continuity in temperature trends, short missing segments in temperature-related variables (TEMP, MAX, and MIN) are now filled using linear interpolation. This approach estimates values between adjacent observations while preserving the underlying temporal structure of the data.

Precipitation values are intentionally excluded from interpolation because rainfall is event-driven rather than continuous. Generating artificial rainfall values between dry and wet days would distort the interpretation of rainfall intensity and extreme precipitation events.

# Exploratory Analysis and Visualisation:  
## 1.Seasonal Cycle Characterisation
To uncover season cycle characteristics,the daily data will first be aggregated into monthly statistics. Monthly aggregation helps reveal the underlying seasonal signal more clearly. For each year, for temperature and dew variables, monthly mean values will be calculated, while for precipitation variables, monthly totals will be computed.This aggregation will produce a dataset where each record represents a specific month and year for each city.  
Planned aggregation:  
  
Temperature → monthly mean  
Precipitation → monthly total  

Once monthly data are generated, the next step will involve computing long-term monthly averages across all years in the dataset. This means that, for each city, all January values across the 25-year period will be averaged together, all February values will be averaged together, and so on. This process will produce a 12-point seasonal cycle representing the typical behaviour of each month.  
### Visualization:  
Following the computation of monthly averages, seasonal patterns will be visualised to examine how weather variables change throughout the year.  
Static visualisations:These plots will be generated using Python libraries such as Matplotlib and Seaborn.  
    1.Monthly seasonal cycle plot (x-axis will have months and the y-axis will have variable(s)).  
    2.Seasonal behaviour between cities: Separate lines in above graph will be plotted for each city, allowing direct comparison of seasonal behaviour across locations.  
    3.Seasonal heatmaps (months are displayed on one axis and years on the other) : Colour intensity will represent the magnitude of variable(s).    

## 2. Inter-annual variability
To analyze year-to-year variability in weather patterns across cities by computing annual statistics from daily observations and visualizing how these metrics change over time.
Daily observations are grouped by city and year.
Metrics calculated: Annual mean temperature , Annual total precipitation, Maximum yearly temperature, Minimum yearly temperature  
### Visualization:
Static Plot: Line Plots (Year vs variable(s)) - For each cities and all cities in same plot.  

## 3. Interactive visualisations
These plots will be developed using Plotly to allow dynamic exploration of seasonal patterns.  
  
  1.multi-city cycle chart: It will be the same as the static line static visualization but here users can toggle individual cities on or off.  
  2.Seasonal behaviour across the entire 25-year dataset: Instead of months/year in X axis we will have date in x axis because hover information will display exact values. This feature is useful for understanding precise seasonal differences between locations. Users can zoom into specific years or seasons to analyse variability.  
  
## 4. Variability
Variability tells us how much weather values fluctuate.  
Daily variability: This reveals whether a city experiences stable weather conditions or large day-to-day changes.  
Yearly variability: Evaluate how stable a city’s climate is across years.    
Using these two scales keeps the analysis clear while still capturing both short-term weather variability and longer-term climate variability.  
Several statistical measures can be used to quantify this spread like: Standard deviation, Variance,Range, Interquartile range (IQR).Among these metrics, standard deviation is most commonly used in climate and meteorological studies because it provides an intuitive measure of how much observations fluctuate around the mean.  
So, we will compute standard deviation , IQR and range for daily and yearly statistics.  
  
### Visualization  
1.For daily variability: Boxplot. A boxplot summarizes the key properties of the distribution, including the median, quartiles, overall spread, and potential outliers.  
2.For yearly variability: Line plot. A jagged, steep-sloped line plot indicates high variability over time compared to a flat, horizontal line, which suggests stability.  
3.Direct Comparison of City Variability:A bar chart of standard deviation provides a simple visual comparison. In this plot, higher bars indicate cities with greater variability in temperature.



## Additional Tasks-1: Trend Analysis Methodology

### Overview
This component implements and evaluates two distinct time series smoothing techniques to further analyze temperature trends across four Indian cities (Mumbai, Delhi, Dehradun, Jaipur) from <Insert years pls>. The analysis also focuses on understanding how methodological choices impact trend interpretation in the meteorological data.

### Methods Implemented

*1. Rolling Window Statistics*
A moving average approach that smooths short-term fluctuations to highlight longer-term trends. Multiple window sizes (7, 30, 90 days) were tested to assess sensitivity to window selection. The centered rolling mean preserves the temporal alignment while reducing noise from daily variations.

*2. Seasonal-Trend Decomposition (STL)*
A robust local regression-based decomposition method that separates the temperature time series into three distinct components:
- **Trend**: Long-term directional changes
- **Seasonal**: Repeating patterns within each year
- **Residual**: Remaining irregular variations and anomalies

*3. Harmonic (Fourier) Analysis*
A spectral decomposition method using Fast Fourier Transform (FFT) that identifies dominant periodic cycles in the data by transforming from the time domain to the frequency domain. This approach quantifies the strength and significance of specific frequencies, revealing cyclical patterns that may not be immediately apparent in the time domain due to the interplay of atmospheric processes.

### Method Comparison

| Aspect | Rolling Average | STL Decomposition | Harmonic Analysis |
|--------|-----------------|-------------------|-------------------|
| **Primary Output** | Smoothed time series | Trend + Seasonal + Residual | Frequency spectrum + dominant cycles |
| **Strengths** | Simple, intuitive, computationally light | Separates overlapping signals, interpretable components | Quantifies cycle strength, detects hidden periodicities |
| **Limitations** | Lags behind data, loses information at boundaries | Multiple parameters to tune, assumes stable seasonality | Assumes linear combinations of sine waves, sensitive to non-stationarity |
| **Best For** | Quick visualization, operational monitoring | Understanding underlying process structure | Identifying and quantifying cyclical patterns |
