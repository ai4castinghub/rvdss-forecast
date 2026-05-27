# test epipredict models
library(epipredict)
library(dplyr)
library(tidyr)
library(lubridate)
library(parsnip)
library(hubValidations)

# shared quantiles and ahead values
quantile_levels <- c(0.025, 0.1, 0.25, 0.5, 0.75, 0.9, 0.975)
ahead_seq <- seq(0, 21, by = 7)

name_dict <- c(
  sarscov2_pct_positive = 'covid',
  rsv_pct_positive = 'rsv',
  flu_pct_positive = 'flu'
)

# load data once
disease_data <- read.csv("auxiliary-data/concatenated_rvdss_data.csv") |>
  mutate(time_value = as.Date(time_value)) |>
  select(-geo_type, -Season)

# ---------------------------
# FORECAST FUNCTIONS (UPDATED)
# ---------------------------

process_disease_flatline_forecaster <- function(disease, data, forecast_date) {
  data <- data[, c("geo_value", "time_value", disease), drop = FALSE] |>
    drop_na() |>
    as_epi_df(geo_value = "geo_value", time_value = "time_value")
  
  data_hist <- data |> filter(time_value < forecast_date)
  
  weekly_results <- lapply(ahead_seq, function(days_ahead) {
    flatline_forecaster(
      data_hist,
      outcome = disease,
      args_list = flatline_args_list(
        ahead = days_ahead,
        quantile_levels = quantile_levels,
        forecast_date = forecast_date
      )
    )
  })
  
  disease_label <- paste("pct wk", name_dict[[disease]], "lab det")
  
  bind_rows(lapply(seq_along(weekly_results), function(i) {
    weekly_results[[i]]$predictions |>
      pivot_quantiles_wider(.pred_distn) |>
      pivot_longer(starts_with("0."),
                   names_to = "output_type_id",
                   values_to = "value") |>
      mutate(
        reference_date = forecast_date,
        disease = disease_label,
        horizon = i - 1,
        value = round(value)
      ) |>
      select(-.pred, -forecast_date)
  }))
}

process_disease_arx_forecaster <- function(disease, data, forecast_date) {
  data <- data[, c("geo_value", "time_value", disease), drop = FALSE] |>
    drop_na() |>
    as_epi_df(geo_value = "geo_value", time_value = "time_value")
  
  data_hist <- data |> filter(time_value < forecast_date)
  
  weekly_results <- lapply(ahead_seq, function(days_ahead) {
    arx_forecaster(
      epi_data = data_hist,
      outcome = disease,
      args_list = arx_args_list(
        ahead = days_ahead,
        quantile_levels = quantile_levels,
        forecast_date = forecast_date
      )
    )
  })
  
  disease_label <- paste("pct wk", name_dict[[disease]], "lab det")
  
  bind_rows(lapply(seq_along(weekly_results), function(i) {
    weekly_results[[i]]$predictions |>
      pivot_quantiles_wider(.pred_distn) |>
      pivot_longer(starts_with("0."),
                   names_to = "output_type_id",
                   values_to = "value") |>
      mutate(
        reference_date = forecast_date,
        disease = disease_label,
        horizon = i - 1,
        value = round(value)
      ) |>
      select(-.pred, -forecast_date)
  }))
}

process_disease_rf_arx_forecaster <- function(disease, data, forecast_date) {
  data <- data[, c("geo_value", "time_value", disease), drop = FALSE] |>
    drop_na() |>
    as_epi_df(geo_value = "geo_value", time_value = "time_value")
  
  data_hist <- data |> filter(time_value < forecast_date)
  
  weekly_results <- lapply(ahead_seq, function(days_ahead) {
    arx_forecaster(
      epi_data = data_hist,
      outcome = disease,
      trainer = rand_forest(mode = "regression") |> set_engine("ranger"),
      args_list = arx_args_list(
        ahead = days_ahead,
        quantile_levels = quantile_levels,
        forecast_date = forecast_date
      )
    )
  })
  
  disease_label <- paste("pct wk", name_dict[[disease]], "lab det")
  
  bind_rows(lapply(seq_along(weekly_results), function(i) {
    weekly_results[[i]]$predictions |>
      pivot_quantiles_wider(.pred_distn) |>
      pivot_longer(starts_with("0."),
                   names_to = "output_type_id",
                   values_to = "value") |>
      mutate(
        reference_date = forecast_date,
        disease = disease_label,
        horizon = i - 1,
        value = round(value)
      ) |>
      select(-.pred, -forecast_date)
  }))
}

process_disease_cdc_baseline_forecaster <- function(disease, data, forecast_date) {
  data <- data[, c("geo_value", "time_value", disease), drop = FALSE] |>
    drop_na() |>
    as_epi_df(geo_value = "geo_value", time_value = "time_value")
  
  data_hist <- data |> filter(time_value < forecast_date)
  
  cdc_results <- cdc_baseline_forecaster(data_hist, outcome = disease)
  
  disease_label <- paste("pct wk", name_dict[[disease]], "lab det")
  
  cdc_results$predictions |>
    pivot_quantiles_wider(.pred_distn) |>
    select(geo_value, ahead, forecast_date, target_date, `0.025`, `0.1`, `0.25`, `0.5`, `0.75`, `0.9`, `0.975`) |>
    pivot_longer(starts_with("0."),
                 names_to = "output_type_id",
                 values_to = "value") |>
    mutate(
      reference_date = forecast_date  + weeks(1),
      disease = disease_label,
      horizon = ahead - 1,
      value = round(value)
    ) |>
    select(-ahead, -forecast_date)|>
    filter(horizon != 4)
}

# ---------------------------
# MAIN FUNCTION
# ---------------------------

run_for_date <- function(forecast_date) {
  
  print(paste("Running:", forecast_date))
  
  all_preds <- bind_rows(lapply(
    names(name_dict),
    process_disease_flatline_forecaster,
    data = disease_data,
    forecast_date = forecast_date
  )) |>
    rename(target_end_date = target_date, location = geo_value, target = disease) |>
    mutate(output_type = "quantile")
  
  all_preds_arx <- bind_rows(lapply(
    names(name_dict),
    process_disease_arx_forecaster,
    data = disease_data,
    forecast_date = forecast_date
  )) |>
    rename(target_end_date = target_date, location = geo_value, target = disease) |>
    mutate(output_type = "quantile")
  
  rf_preds <- bind_rows(lapply(
    names(name_dict),
    process_disease_rf_arx_forecaster,
    data = disease_data,
    forecast_date = forecast_date
  )) |>
    rename(target_end_date = target_date, location = geo_value, target = disease) |>
    mutate(output_type = "quantile")
  
  cdc_baseline_preds <- bind_rows(lapply(
    names(name_dict),
    process_disease_cdc_baseline_forecaster,
    data = disease_data,
    forecast_date = forecast_date
  )) |>
    rename(target_end_date = target_date, location = geo_value, target = disease) |>
    mutate(output_type = "quantile")
  
  # file paths
  all_preds_path <- paste0("model-output/AI4Casting_Hub-Flatline/", forecast_date, "-AI4Casting_Hub-Flatline.csv")
  all_preds_arx_path <- paste0("model-output/AI4Casting_Hub-Quantile_AR/", forecast_date, "-AI4Casting_Hub-Quantile_AR.csv")
  rf_preds_path <- paste0("model-output/AI4Casting_Hub-RF_Quantile_AR/", forecast_date, "-AI4Casting_Hub-RF_Quantile_AR.csv")
  cdc_baseline_preds_path <- paste0("model-output/AI4Casting_Hub-Quantile_Baseline/", forecast_date, "-AI4Casting_Hub-Quantile_Baseline.csv")
  
  write.csv(all_preds, all_preds_path, row.names = FALSE)
  write.csv(all_preds_arx, all_preds_arx_path, row.names = FALSE)
  write.csv(rf_preds, rf_preds_path, row.names = FALSE)
  write.csv(cdc_baseline_preds, cdc_baseline_preds_path, row.names = FALSE)
}

# ---------------------------
# RUN FOR ALL DATES
# ---------------------------

forecast_dates <- seq(
  from = as.Date("2026-04-04"), #as.Date("2025-09-06"),
  to   = as.Date("2026-05-09"),
  by   = "7 days"
)

lapply(forecast_dates, run_for_date)