# Model Outputs Folder Overview

This folder contains subdirectories for each model, which hold the submitted model output files. The structure and contents of these directories follow the [model output guidelines in the Hubverse documentation](https://docs.hubverse.io/en/latest/user-guide/model-output.html). Below, we outline instructions specifically for AI4Casting Hub submissions.

# Data Submission Instructions

Submit all forecasts directly to the [model-output/](./) folder by creating a pull request. This process ensures that automatic data validation checks are performed.

These instructions cover details on [data formatting](#Data-formatting) and [forecast validation](#Forecast-validation), which you can perform before submitting the pull request. Additionally, [metadata](https://github.com/ai4castinghub/rvdss-forecast/blob/main/model-metadata/README.md) required for each model should be provided in the model-metadata folder.

**Table of Contents**:
- [What is a forecast](#What-is-a-forecast)
- [Target data](#Target-data)
- [Data formatting](#Data-formatting)
- [Forecast file format](#Forecast-file-format)
- [Forecast data validation](#Forecast-validation)
- [Policy on late submissions](#policy-on-late-or-updated-submissions)

## What is a Forecast?

Forecasts are quantitative predictions about data to be observed in the future. These are considered "unconditional" predictions, meaning they should represent uncertainty across all possible future scenarios, not just specific ones (like increased vaccination rates or new social-distancing policies). Forecasts submitted here will be evaluated against actual observed data.

## Target Data

This project focuses on percentage of positive lab detection tests data for COVID-19, influenza, and RSV, as reported in the [Respiratory Virus Detection Surveillance System](https://www.canada.ca/en/public-health/services/surveillance/respiratory-virus-detections-canada.html). This data serves as the target ("gold standard") for forecasts. Further details can be found in the [target-data folder README](../target-data/season_2026_2027/README.md).

## Data Formatting

Automatic checks validate the filename and contents of forecast files to ensure compatibility with visualization and ensemble forecasting.

### Subdirectory

Each model submitting forecasts will have a unique subdirectory in the [model-output/](model-output/) directory. The subdirectory should be named as follows:

    team-model

Where:
- `team` is the team name
- `model` is the model name

Both `team` and `model` should be under 15 characters and not contain special characters, except for underscores (`_`). Each team-model combination must be unique.

### Metadata

The metadata file for each model must follow this naming convention and be placed in the model-metadata directory:

    team-model.yml

For more details, see the [model-metadata README](https://github.com/ai4castinghub/rvdss-forecast/blob/main/model-metadata/README.md).

### Forecasts

Each forecast file should be named as follows:

    YYYY-MM-DD-team-model.csv

Where:
- `YYYY` is the 4-digit year
- `MM` is the 2-digit month
- `DD` is the 2-digit day
- `team` is the team name
- `model` is the model name

The `YYYY-MM-DD` date should be the current round's Saturday (the same Saturday for a Saturday submission) and match the `reference_date` inside the file. The `team` and `model` in the filename must match the subdirectory names.

## Forecast File Format

The forecast file should be a CSV with the following columns:

- `reference_date`
- `target`
- `horizon`
- `target_end_date`
- `location`
- `output_type`
- `output_type_id`
- `value`

No additional columns are allowed.

Each row in the file represents a quantile prediction for a specific location, date, and horizon.

### `reference_date`

This date (in `YYYY-MM-DD` format) indicates when the forecast is made. It should be the current round's Saturday, whether the file is submitted on Friday or Saturday.

### `target`

This column must contain one of the following target strings:
- `pct wk covid lab det`
- `pct wk flu lab det`
- `pct wk rsv lab det`

### `horizon`

Indicates the number of weeks between the `reference_date` and the `target_end_date`. A horizon of `0` represents a nowcast, while a horizon of `1` represents a forecast for the following week.

### `target_end_date`

The last date of the forecast target’s week, formatted as `YYYY-MM-DD`. It is the Saturday at the end of the forecasted week.

### `location`

This should match one of the "locations_abbr" in the [location information file](../auxiliary-data/locations.csv).

### `output_type`

Currently, this column should be set to "quantile," representing quantile forecasts for percentage positive lab detections.

    0.###

### `output_type_id`

For quantile forecasts, this column specifies the quantile probability level, formatted as `0.###`. This value indicates the quantile probability level for for the
`value` in this row.

Teams must provide the following 7 quantiles:

0.025, 0.1, 0.25, 0.5, 0.75, 0.9 and 0.975


### `value`

Values in the `value` column are non-negative numbers indicating the "quantile" prediction for this row. For a "quantile" prediction, `value` is the inverse of the cumulative distribution function (CDF) for the target, location, and quantile associated with that row. For example, the 2.5 and 97.5 quantiles for a given target and location should capture 95% of the predicted values and correspond to the central 95% Prediction Interval. 

### Example tables

**Table 1:** This table represents a forecast for the week ending on 2026-10-17 for percentage positive flu lab detections in the Ontario province. The forecast includes quantile predictions ranging from the 2.5th to the 97.5th percentiles. The horizon of -1 indicates this is a hindcast for the previous week relative to the reference_date of 2026-10-24.

| reference_date | target             | horizon | location | target_end_date | output_type | output_type_id | value |
|----------------|--------------------|---------|----------|-----------------|-------------|----------------|-------|
| 2026-10-24     | pct wk flu lab det | -1      | on       | 2026-10-17      | quantile    | 0.025          | 3.0   |
| 2026-10-24     | pct wk flu lab det | -1      | on       | 2026-10-17      | quantile    | 0.1            | 3.2   |
| 2026-10-24     | pct wk flu lab det | -1      | on       | 2026-10-17      | quantile    | 0.25           | 3.3   |
| 2026-10-24     | pct wk flu lab det | -1      | on       | 2026-10-17      | quantile    | 0.5            | 3.5   |
| 2026-10-24     | pct wk flu lab det | -1      | on       | 2026-10-17      | quantile    | 0.75           | 3.7   |
| 2026-10-24     | pct wk flu lab det | -1      | on       | 2026-10-17      | quantile    | 0.9            | 3.8   |
| 2026-10-24     | pct wk flu lab det | -1      | on       | 2026-10-17      | quantile    | 0.975          | 4.0   |



## Forecast validation 

To ensure proper data formatting, pull requests for new data in
`model-output/` will be automatically run. Optionally, you may also run these validations locally.

### Pull request forecast validation

When a pull request is submitted, the data are validated through [Github
Actions](https://docs.github.com/en/actions) which runs the tests to validate the requirements above. Please
[let us know](https://github.com/ai4castinghub/rvdss-forecast/issues) if you are facing issues while running the tests.

### Local forecast validation

Optionally, you may validate a forecast file locally before submitting it to the hub in a pull request. Note that this is not required, since the validations will also run on the pull request. To run the validations locally, follow these steps:

1. Create a fork of the `rvdss-forecast` repository and then clone the fork to your computer.
2. Create a draft of the model submission file for your model and place it in the `model-output/<your model id>` folder of this clone.
3. Install the hubValidations package for R by running the following command from within an R session:
``` r
install.packages("hubValidations", repos = c("https://hubverse-org.r-universe.dev", "https://cloud.r-project.org"))
```
4. Validate your draft forecast submission file by running the following command in an R session:
``` r
library(hubValidations)
hubValidations::validate_submission(
    hub_path="<path to your clone of the hub repository>",
    file_path="<path to your file, relative to the model-output folder>")
```

For example, if your working directory is the root of the hub repository, you can use a command similar to the following:
``` r
library(hubValidations)
hubValidations::validate_submission(
    hub_path=".",
    file_path="F-trends/2026-10-24-F-trends.csv")
```
The function returns the output of each validation check.

If all is well, all checks should either be prefixed with a `✔` indicating success or `ℹ` indicating a check was skipped, e.g.:
```
✔ 2026-10-24-F-trends.csv: File exists at path model-output/F-trends/2026-10-24-F-trends.csv.
✔ 2026-10-24-F-trends.csv: File name "2026-10-24-F-trends.csv" is valid.
✔ 2026-10-24-F-trends.csv: File directory name matches `model_id` metadata in file name.
✔ 2026-10-24-F-trends.csv: `round_id` is valid.
✔ 2026-10-24-F-trends.csv: File is accepted hub format.
...
```

If there are any failed checks or execution errors, the check's output will be prefixed with a `✖` or `!` and include a message describing the problem.

To get an overall assessment of whether the file has passed validation checks, you can pass the output of `validate_submission()` to `check_for_errors()`
```r
library(hubValidations)

validations <- validate_submission(
    hub_path = ".",
    file_path = "F-trends/2026-10-24-F-trends.csv")

check_for_errors(validations)
```
If the file passes all validation checks, the function will return the following output:

```r
✔ All validation checks have been successful.
```
If test failures or execution errors are detected, the function throws an error and prints the affected checks. Local Hubverse validation checks the time at which you run it; the pull-request workflow separately checks the PR event timestamp against the 2026–27 11:30 p.m. deadline.


## Policy on late or updated submissions 

For the 2026–27 season, forecasts are due by 11:30 p.m. America/Toronto time on each reference Saturday, from October 24, 2026 through May 29, 2027. The pull request must be opened or updated with the forecast by the deadline; a later update is late. The submission check uses the pull request event timestamp, so a validation run that finishes after 11:30 p.m. does not itself make an on-time submission late. We do not accept late forecasts.

The hub's own retrospective model backfills run separately on Mondays and are not on-time team submissions.

## Evaluation criteria
Forecasts will be evaluated using `Weighted Interval Score (WIS)`, `Absolute Error (AE)` and `Mean Squared Error (MSE)`. The CMU [Delphi group's Forecast Evaluation Dashboard](https://delphi.cmu.edu/forecast-eval/) and the COVID-19 Forecast Hub periodic [Forecast Evaluation Reports](https://covid19forecasthub.org/eval-reports/) provide examples of evaluations using these criteria.
