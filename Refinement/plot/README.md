# Anomaly Refinement Plots

This folder now focuses only on the anomaly-threshold refinement part.

The plots read the CSV result tables already saved in `Refinement/results/` and
save figure files into `Refinement/plot/figures/`.

The code is now self-contained inside `plot_anomaly_refinement.py` so it can be
imported directly into the dashboard without a separate common helper or a run-all
script.

Files:

- `__init__.py`
- `plot_anomaly_refinement.py`

Run from the project root:

```powershell
python Refinement/plot/plot_anomaly_refinement.py
```

You can also import it in Python:

```python
from Refinement.plot import ensure_anomaly_plots, get_anomaly_plot_paths
```

This makes 4 focused plots:

- threshold vs composite score
- missingness vs residual-outlier trade-off
- anomaly values removed across thresholds
- residual outlier heatmap by city and threshold
