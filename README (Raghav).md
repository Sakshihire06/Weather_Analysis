# Weather Data Analysis — Indian Cities
**Mumbai · Delhi · Dehradun · Jaipur | 2000–2024**



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

