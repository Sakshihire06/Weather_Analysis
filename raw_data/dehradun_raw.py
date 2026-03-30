import pandas as pd
import requests
import time
import random
import io
import xarray as xr
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

CITY_NAME  = 'Dehradun'
STATION_ID = '42111099999'
LAT        = 30.32
LON        = 78.03

START_YEAR = 2000
END_YEAR   = 2024

# had to use session because plain requests was giving 503 errors from noaa
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.ncei.noaa.gov/',
})


def download_one_year(station_id, year):
    url = f'https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/{year}/{station_id}.csv'
    for attempt in range(4):
        try:
            time.sleep(random.uniform(0.4, 1.0))
            r = session.get(url, timeout=25)
            if r.status_code == 200 and len(r.content) > 200:
                return year, pd.read_csv(io.StringIO(r.text), low_memory=False)
            elif r.status_code in (503, 429):
                # server busy, wait a bit and retry
                time.sleep((2 ** attempt) + random.uniform(0, 0.5))
            else:
                break
        except Exception:
            time.sleep(2 ** attempt)
    return year, None


def get_raw_data():
    local_nc = Path(__file__).resolve().parent / 'nc_raw' / 'dehradun_raw.nc'
    if local_nc.exists():
        df = xr.open_dataset(local_nc).to_dataframe().reset_index()
        print(f'loaded local raw data for {CITY_NAME}  {len(df)} rows - dehradun_raw.py:50')
        return df

    years = list(range(START_YEAR, END_YEAR + 1))
    frames = {}

    # downloading 3 years at a time to make it faster
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(download_one_year, STATION_ID, yr): yr for yr in years}
        for future in as_completed(futures):
            year, df = future.result()
            if df is not None:
                frames[year] = df
                print(f'downloaded {CITY_NAME} {year}  {len(df)} rows - dehradun_raw.py:63')
            else:
                print(f'skipped {CITY_NAME} {year}  no data - dehradun_raw.py:65')

    if not frames:
        print(f'something went wrong, no data for {CITY_NAME} - dehradun_raw.py:68')
        return pd.DataFrame()

    combined = pd.concat([frames[y] for y in sorted(frames)], ignore_index=True)
    combined['CITY'] = CITY_NAME
    print(f'{CITY_NAME} done  {len(combined)} rows total - dehradun_raw.py:73')
    return combined


if __name__ == '__main__':
    df = get_raw_data()
    print(df.head())
