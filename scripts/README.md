# Hub-generated forecasts

Run commands from the repository root. `hub_model_forecasts.R` is the single generator for the four `epipredict` models: Flatline, Quantile AR, RF Quantile AR, and Quantile Baseline (CDC baseline). It reads the archived and current `target_rvdss_data.csv` files directly, so it does not depend on a separately refreshed concatenated data file.

```sh
Rscript scripts/hub_model_forecasts.R
Rscript scripts/hub_model_forecasts.R --reference-date 2026-10-24
Rscript scripts/hub_model_forecasts.R --from 2026-10-24 --to 2026-11-07
Rscript scripts/hub_model_forecasts.R --reference-date 2026-10-24 --overwrite
```

Without an explicit date, the script uses the most recent Saturday in `America/Toronto`. The [forecast workflow](../.github/workflows/hub-model-outputs.yml) runs Mondays at 10:30 a.m. Toronto time: its first 2026–27 backfill is October 26 for the October 24 round; its last is May 31 for the May 29 round. Runs outside the season skip automatically. Manual date ranges must contain Saturday endpoints.

For each reference Saturday, the script requires observations for the preceding Saturday from the Friday RVDSS update. It uses only observations on or before that date, then generates horizons 0–3, seven configured quantiles, and the existing four model IDs. Existing output files are left untouched unless `--overwrite` is given. Each new file receives structural checks and Hubverse validation.

These Monday-generated hub forecasts are retrospective backfills, **not on-time team submissions**. The script skips Hubverse's submission-time check for these hub-owned files; team pull requests still have the Saturday 11:30 p.m. `America/Toronto` cutoff. Historical backfills use the currently available revised truth data, not an archived Friday vintage, so they should not be interpreted as strictly real-time forecasts.

The ensemble remains a separate, manually run script. It combines available model-output files for a reference date, excludes prior ensemble/GPT outputs, and does not invoke `epipredict`:

```sh
Rscript scripts/all_hub_ensemble.R --reference-date 2026-10-24
```

The Monday workflow runs on Ubuntu 22.04 and installs `epipredict`, `epiprocess`, `dplyr`, `tidyr`, `parsnip`, `ranger`, and `hubValidations` through the shared [R setup action](../.github/actions/setup-forecast-r/action.yml). The [dependency cache workflow](../.github/workflows/cache-deps.yaml) warms the same installed-package cache daily; the Monday job also installs any packages missing from the cache. The Friday data workflow likewise restores a pip download cache keyed to `requirements.txt` and installs its Python requirements before fetching data. These caches speed up runs but are not required for correctness. The ensemble script additionally requires `hubUtils` and `hubEnsembles` when run manually.
