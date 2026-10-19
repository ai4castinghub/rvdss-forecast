# Generate the four AI4Casting Hub epipredict model submissions.
# Run from the repository root. Example:
# Rscript scripts/hub_model_forecasts.R --reference-date 2026-10-24
# Rscript scripts/hub_model_forecasts.R --from 2026-10-24 --to 2026-11-07
required_packages <- c("epipredict", "epiprocess", "dplyr", "tidyr",
                       "parsnip", "ranger", "hubValidations")

quantile_levels <- c(0.025, 0.1, 0.25, 0.5, 0.75, 0.9, 0.975)
horizons <- 0:3
target_names <- c(
  sarscov2_pct_positive = "pct wk covid lab det",
  rsv_pct_positive = "pct wk rsv lab det",
  flu_pct_positive = "pct wk flu lab det"
)
model_ids <- c(
  flatline = "AI4Casting_Hub-Flatline",
  arx = "AI4Casting_Hub-Quantile_AR",
  rf_arx = "AI4Casting_Hub-RF_Quantile_AR",
  cdc = "AI4Casting_Hub-Quantile_Baseline"
)

parse_reference_date <- function(value) {
  parsed <- as.Date(value, format = "%Y-%m-%d")
  if (is.na(parsed) || format(parsed, "%Y-%m-%d") != value ||
      as.POSIXlt(parsed)$wday != 6) {
    stop("Reference dates must be valid Saturdays in YYYY-MM-DD format: ", value)
  }
  parsed
}

previous_reference_date <- function(today = as.Date(Sys.time(), tz = "America/Toronto")) {
  today - ((as.POSIXlt(today)$wday + 1L) %% 7L)
}

parse_options <- function(args) {
  options <- list(from = NULL, to = NULL, overwrite = FALSE,
                  explicit_dates = FALSE)
  seen <- character(0)
  i <- 1L
  while (i <= length(args)) {
    arg <- args[[i]]
    if (arg == "--overwrite") {
      options$overwrite <- TRUE
    } else if (arg %in% c("--reference-date", "--from", "--to")) {
      if (arg %in% seen) stop("Duplicate option: ", arg)
      if ((arg == "--reference-date" && any(c("--from", "--to") %in% seen)) ||
          (arg %in% c("--from", "--to") && "--reference-date" %in% seen)) {
        stop("--reference-date cannot be combined with --from or --to")
      }
      if (i == length(args)) stop("Missing date after ", arg)
      value <- parse_reference_date(args[[i + 1L]])
      options$explicit_dates <- TRUE
      if (arg == "--reference-date") {
        options$from <- value
        options$to <- value
      } else {
        options[[substring(arg, 3L)]] <- value
      }
      seen <- c(seen, arg)
      i <- i + 1L
    } else {
      stop("Unknown option: ", arg)
    }
    i <- i + 1L
  }
  if (is.null(options$from) && is.null(options$to)) {
    options$from <- previous_reference_date()
    options$to <- options$from
  }
  if (is.null(options$from) || is.null(options$to) || options$from > options$to) {
    stop("Provide a valid --from and --to range")
  }
  options
}

load_data <- function() {
  season_file <- function(year) {
    folder <- if (year <= 2024L) {
      "auxiliary-data/target-data-archive"
    } else {
      "target-data"
    }
    file.path(folder, paste0("season_", year, "_", year + 1L),
              "target_rvdss_data.csv")
  }
  # Read current data first so its revisions win if seasons overlap.
  files <- vapply(2026:2019, season_file, character(1))
  files <- files[file.exists(files)]
  if (length(files) == 0L) stop("No RVDSS target data files found")
  data <- dplyr::bind_rows(lapply(files, function(path) {
    read.csv(path, stringsAsFactors = FALSE)
  }))
  required <- c("geo_value", "time_value", names(target_names))
  missing <- setdiff(required, names(data))
  if (length(missing) > 0L) stop("Missing source columns: ", paste(missing, collapse = ", "))
  data$time_value <- as.Date(data$time_value)
  if (anyNA(data$time_value)) stop("Source data contains invalid time_value dates")
  data$geo_value[data$geo_value == "yk"] <- "yt"
  # Historical and current season files can overlap at a boundary.
  data |>
    dplyr::distinct(.data$geo_value, .data$time_value, .keep_all = TRUE) |>
    dplyr::arrange(.data$geo_value, .data$time_value)
}

prepare_epi_data <- function(data, disease, origin_date) {
  current_locations <- data |>
    dplyr::filter(.data$time_value == origin_date, !is.na(.data[[disease]])) |>
    dplyr::pull(.data$geo_value) |>
    unique()
  if (length(current_locations) == 0L) {
    stop("No current ", disease, " observations for ", origin_date,
         "; run the Friday data update before forecasting.")
  }
  data |>
    dplyr::filter(.data$time_value <= origin_date,
                  .data$geo_value %in% current_locations) |>
    dplyr::select(dplyr::all_of(c("geo_value", "time_value", disease))) |>
    tidyr::drop_na() |>
    epiprocess::as_epi_df(as_of = origin_date + 6L, signal_format = "as_is")
}

run_forecaster <- function(model, epi_data, disease, origin_date, seed) {
  ahead_days <- 7L * (horizons + 1L)
  if (model == "cdc") {
    set.seed(seed)
    return(epipredict::cdc_baseline_forecaster(
      epi_data, outcome = disease,
      args_list = epipredict::cdc_baseline_args_list(
        data_frequency = "1 week", aheads = 1:4,
        forecast_date = origin_date, quantile_levels = quantile_levels
      )
    )$predictions)
  }
  dplyr::bind_rows(lapply(ahead_days, function(ahead) {
    if (model == "flatline") {
      fit <- epipredict::flatline_forecaster(
        epi_data, outcome = disease,
        args_list = epipredict::flatline_args_list(
          ahead = ahead, forecast_date = origin_date,
          quantile_levels = quantile_levels
        )
      )
    } else {
      trainer <- if (model == "rf_arx") {
        parsnip::rand_forest(mode = "regression") |>
          parsnip::set_engine("ranger", seed = seed)
      } else {
        NULL
      }
      set.seed(seed)
      args <- epipredict::arx_args_list(
        ahead = ahead, forecast_date = origin_date,
        quantile_levels = quantile_levels
      )
      fit <- if (is.null(trainer)) {
        epipredict::arx_forecaster(epi_data, outcome = disease, args_list = args)
      } else {
        epipredict::arx_forecaster(
          epi_data, outcome = disease, trainer = trainer, args_list = args
        )
      }
    }
    fit$predictions
  }))
}

format_wide_submission <- function(wide, disease, reference_date) {
  quantile_columns <- as.character(quantile_levels)
  missing <- setdiff(quantile_columns, names(wide))
  if (length(missing) > 0L) stop("Missing forecast quantiles: ", paste(missing, collapse = ", "))
  wide |>
    tidyr::pivot_longer(
      cols = dplyr::all_of(quantile_columns),
      names_to = "output_type_id", values_to = "value"
    ) |>
    dplyr::transmute(
      reference_date = reference_date,
      target = unname(target_names[[disease]]),
      horizon = as.integer((as.Date(.data$target_date) - reference_date) / 7),
      target_end_date = as.Date(.data$target_date),
      location = .data$geo_value,
      output_type = "quantile",
      output_type_id = as.numeric(.data$output_type_id),
      # Preserve the rounding convention used by the previous hub scripts.
      value = pmax(0, dplyr::case_when(
        .data$output_type_id < 0.5 ~ floor(.data$value),
        .data$output_type_id > 0.5 ~ ceiling(.data$value),
        TRUE ~ round(.data$value)
      ))
    )
}

format_submission <- function(predictions, disease, reference_date) {
  wide <- epipredict::pivot_quantiles_wider(predictions, .pred_distn)
  format_wide_submission(wide, disease, reference_date)
}

check_submission <- function(submission, reference_date,
                             allowed_horizons = horizons) {
  if (nrow(submission) == 0L) stop("Forecaster produced no rows")
  if (anyNA(submission) || any(!is.finite(submission$value)) ||
      any(submission$value < 0)) stop("Forecast contains missing or invalid values")
  if (any(!submission$horizon %in% allowed_horizons) ||
      any(submission$target_end_date != reference_date + 7L * submission$horizon)) {
    stop("Forecast target dates do not match the configured horizons")
  }
  keys <- c("reference_date", "target", "horizon", "target_end_date",
            "location", "output_type", "output_type_id")
  if (anyDuplicated(submission[keys])) stop("Forecast contains duplicate quantile rows")
  groups <- submission |>
    dplyr::group_by(.data$target, .data$location, .data$horizon) |>
    dplyr::summarise(
      n = dplyr::n(),
      ordered = all(diff(.data$value[order(.data$output_type_id)]) >= 0),
      .groups = "drop"
    )
  if (any(groups$n != length(quantile_levels)) || any(!groups$ordered)) {
    stop("Forecast quantiles are incomplete or decreasing")
  }
  invisible(submission)
}

output_path <- function(model_id, reference_date) {
  file.path("model-output", model_id,
            paste0(reference_date, "-", model_id, ".csv"))
}

run_round <- function(reference_date, data, overwrite) {
  # Friday's dashboard release reports the week ending one Saturday earlier.
  # Monday backfills the round whose reference Saturday has just passed.
  origin_date <- reference_date - 7L
  if (!origin_date %in% data$time_value) {
    stop("Missing observations for ", origin_date,
         "; the preceding Friday data update must complete before backfilling ",
         reference_date)
  }
  message("Generating ", reference_date, " forecasts from data through ", origin_date)
  for (model in names(model_ids)) {
    model_id <- unname(model_ids[[model]])
    path <- output_path(model_id, reference_date)
    if (file.exists(path) && !overwrite) {
      message("Already exists, skipping ", path, " (use --overwrite to regenerate)")
      next
    }
    submission <- dplyr::bind_rows(lapply(seq_along(target_names), function(i) {
      disease <- names(target_names)[[i]]
      epi_data <- prepare_epi_data(data, disease, origin_date)
      seed <- as.integer(format(reference_date, "%Y%m%d")) + 100L * i +
        match(model, names(model_ids))
      predictions <- run_forecaster(model, epi_data, disease, origin_date, seed)
      format_submission(predictions, disease, reference_date)
    }))
    check_submission(submission, reference_date)
    dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
    write.csv(submission, path, row.names = FALSE)
    validation <- hubValidations::validate_submission(
      hub_path = ".", file_path = file.path(model_id, basename(path)),
      skip_submit_window_check = TRUE
    )
    hubValidations::check_for_errors(validation, verbose = TRUE)
    message("Wrote and validated ", path)
  }
}

if (sys.nframe() == 0L) {
  if (!file.exists("hub-config/tasks.json")) {
    stop("Run this script from the repository root")
  }
  args <- commandArgs(trailingOnly = TRUE)
  env_reference_date <- Sys.getenv("FORECAST_REFERENCE_DATE", "")
  if (nzchar(env_reference_date)) {
    args <- c(args, "--reference-date", env_reference_date)
  }
  if (tolower(Sys.getenv("FORECAST_OVERWRITE", "false")) == "true") {
    args <- c(args, "--overwrite")
  }
  options <- parse_options(args)
  if (!options$explicit_dates &&
      (options$from < as.Date("2026-10-24") ||
       options$from > as.Date("2027-05-29"))) {
    message("No 2026-27 forecast round to backfill this Monday")
    quit(status = 0L)
  }
  missing_packages <- required_packages[!vapply(required_packages,
                                                requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing_packages) > 0L) {
    stop("Install required R packages: ", paste(missing_packages, collapse = ", "))
  }
  source_data <- load_data()
  for (date_string in as.character(seq(options$from, options$to, by = "7 days"))) {
    run_round(as.Date(date_string), source_data, options$overwrite)
  }
}
