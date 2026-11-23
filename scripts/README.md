# Hub-generated forecasts

Run commands from the repository root. `hub_model_forecasts.R` is the single generator for the four `epipredict` models: Flatline, Quantile AR, RF Quantile AR, and Quantile Baseline (CDC baseline). It reads the archived and current `target_rvdss_data.csv` files directly, so it does not depend on a separately refreshed concatenated data file.

```sh
Rscript scripts/hub_model_forecasts.R
Rscript scripts/hub_model_forecasts.R --reference-date 2026-10-24
Rscript scripts/hub_model_forecasts.R --from 2026-10-24 --to 2026-11-07
Rscript scripts/hub_model_forecasts.R --reference-date 2026-10-24 --overwrite
```

Without an explicit date, the script uses the most recent Saturday in `America/Toronto`. The [weekly pipeline](../.github/workflows/hub-model-outputs.yml) starts Mondays at 10:00 a.m. Toronto time: its first backfill for the 2026–27 challenge is November 23 for the November 21 round; its last is May 31 for the May 29 round. The forecast and ensemble stages skip rounds outside the season automatically. Manual date ranges must contain Saturday endpoints.

For each reference Saturday, the script requires observations for the preceding Saturday from the Friday RVDSS update. It uses only observations on or before that date, then generates horizons 0–3, seven configured quantiles, and the existing four model IDs. Existing output files are left untouched unless `--overwrite` is given. Each new file receives structural checks and Hubverse validation.

These Monday-generated hub forecasts are retrospective backfills, **not on-time team submissions**. The script skips Hubverse's submission-time check for these hub-owned files; team pull requests still have the Saturday 11:30 p.m. `America/Toronto` cutoff. Historical backfills use the currently available revised truth data, not an archived Friday vintage, so they should not be interpreted as strictly real-time forecasts.

The Monday job concatenates data, generates the four hub models, refreshes model data, runs `all_hub_ensemble.R` for both ensembles, then refreshes model data again. Use `--models-only` to skip truth concatenation.

`Simple_Ens` replaces `Ensemble_v1` from November 14, 2026, preserving historical outputs. It averages available quantiles per task from `auxiliary-data/concatenated_model_output.csv`, excluding hub Flatline, Quantile_Baseline, both GPT_4o IDs, Team_Ens, Ensemble_v1, Weighted_Ensemble, and itself.

`Team_Ens` averages available quantiles with equal weight per external model marked `designated_model: true`, including external hub ensembles, at horizons 0–3. One model is sufficient; no eligible submissions means no output. Forecasts go under `model-output/AI4Casting_Hub-Team_Ens/`.

Backfill both ensembles without regenerating components; add `--overwrite` to replace existing forecasts:

```sh
Rscript scripts/build_concatenated_rvdss_target_and_forecast.R --models-only
Rscript scripts/all_hub_ensemble.R --reference-date 2026-11-14
Rscript scripts/build_concatenated_rvdss_target_and_forecast.R --models-only
```

Reports show only `Simple_Ens` in the ensemble panel and exclude `Simple_Ens`, `Team_Ens`, and `Ensemble_v1` from individual-model plots. Reports before November 14, 2026 are preserved. Regenerate that date with:

```sh
python scripts/rvdss-report.py --reference-date 2026-11-14
```

The Monday workflow runs on Ubuntu 22.04 and installs the forecaster, concatenation, validation, and ensemble packages through the shared [R setup action](../.github/actions/setup-forecast-r/action.yml). The [dependency cache workflow](../.github/workflows/cache-deps.yaml) warms the same installed-package cache daily; the Monday job also installs any packages missing from the cache. The Friday data workflow likewise restores a pip download cache keyed to `requirements.txt` and installs its Python requirements before fetching data. These caches speed up runs but are not required for correctness.
