# Refinement Work

This folder contains three separate refinement experiments, each implemented in its own Python file:

- `1_smoothing_refinement.py`
- `2_anomaly_threshold_refinement.py`
- `3_extreme_event_refinement.py`

All generated result CSV files are saved in `Refinement/results/`.

The refinement scripts now read from the saved cleaned datasets in
`cleaned_data/nc_cleaned/` so they do not duplicate the repo's cleaning and
unit-conversion pipeline.

Run them from the project root with:

```powershell
python Refinement/1_smoothing_refinement.py
python Refinement/2_anomaly_threshold_refinement.py
python Refinement/3_extreme_event_refinement.py
```
