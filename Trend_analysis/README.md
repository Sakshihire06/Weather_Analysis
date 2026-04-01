# Trend Analysis Module

This module implements three complementary smoothing and decomposition methods for weather data analysis.

## Methods Implemented

1. **Rolling Average** - Moving window smoothing with multiple window sizes (7, 30, 90 days)
2. **STL Decomposition** - Seasonal-Trend decomposition using LOESS
3. **Harmonic Analysis** - Fourier-based harmonic reconstruction

## How to Import

### Import all functions:
```python
from Trend_analysis import (
    load_all_cities,
    rolling_average,
    stl_decomposition,
    harmonic_analysis,
    compare_methods,
    run_all_analysis
)
