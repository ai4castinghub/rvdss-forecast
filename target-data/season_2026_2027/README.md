# RVDSS target data, 2026–27

The Friday data update workflow writes `target_rvdss_data.csv` here after the Public Health Agency of Canada's [RVDSS dashboard](https://www.canada.ca/en/public-health/services/surveillance/respiratory-virus-detections-canada.html) is updated. The first planned update is Friday, October 23, 2026. The CSV is not available until the first successful update.

The file contains one row per reported week and location. `time_value` is the Saturday ending the epidemiological week; `geo_type` and `geo_value` identify the location; and `flu_pct_positive`, `rsv_pct_positive`, and `sarscov2_pct_positive` are the percentages used as forecast targets. Published values may be revised in later Friday updates.

Forecast submissions use the following Saturday as `reference_date`. The first reference date is October 24, 2026, and the last is May 29, 2027. Horizon −1 uses the preceding Saturday's target data; horizon 0 uses the reference Saturday; horizons 1–3 use the next three Saturdays. The last horizon-3 target ends June 19, 2027, so data updates must continue long enough to evaluate it.

The workflow also stores source tables in `auxiliary-data/season_2026_2027_raw_files/`. See [the updater](../../scripts/rvdss_update.py) for the transformation and [the challenge README](../../README.md) for submission dates.
