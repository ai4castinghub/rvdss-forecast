# Hub configuration files

This folder contains configuration files for the Hub, following the recommended [Hub configuration files in Hubverse's documentation.](https://hubverse.io/en/latest/user-guide/hub-config.html)

`tasks.json` includes Saturday reference dates from October 24, 2026 through May 29, 2027, while retaining older seasons for historical validation. The allowed target dates extend through June 19, 2027 for three-week-ahead forecasts. `admin.json` sets the hub timezone to `America/Toronto`.

The Hubverse `submissions_due` window is date-based and cannot express the 11:30 p.m. Saturday cutoff. The pull-request validation workflow enforces that cutoff separately for 2026–27 submissions. The existing `start: -6` allows submissions earlier in the week; teams should use Friday's newly released RVDSS data when preparing forecasts.
