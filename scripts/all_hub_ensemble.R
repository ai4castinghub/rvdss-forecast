# Generate the hub ensemble separately from the four epipredict models.
# Run from the repository root after refreshing the concatenated model output.
# Rscript scripts/all_hub_ensemble.R --reference-date 2026-10-24
source("scripts/hub_model_forecasts.R", local = TRUE)

ensemble_id <- "AI4Casting_Hub-Ensemble_v1"
excluded_models <- c(
  ensemble_id,
  "AI4Casting_GPT_4o",
  "AI4Casting_Hub-GPT_4o",
  "AI4Casting_Hub-Weighted_Ensemble"
)

load_components <- function(reference_date) {
  path <- "auxiliary-data/concatenated_model_output.csv"
  if (!file.exists(path)) stop("Missing concatenated model output: ", path)
  data <- read.csv(path, stringsAsFactors = FALSE)
  columns <- c("reference_date", "target", "horizon", "target_end_date",
               "location", "output_type", "output_type_id", "value", "model")
  missing <- setdiff(columns, names(data))
  if (length(missing)) stop("Concatenated model output is missing: ",
                            paste(missing, collapse = ", "))
  data <- data[data$reference_date == as.character(reference_date) &
                 !data$model %in% excluded_models, columns, drop = FALSE]
  if (nrow(data) == 0L) stop("No component forecasts for ", reference_date)
  message("Ensembling ", length(unique(data$model)), " models for ", reference_date)
  data$model_id <- data$model
  data$model <- NULL
  data$reference_date <- as.Date(data$reference_date)
  data$target_end_date <- as.Date(data$target_end_date)
  data$output_type_id <- as.numeric(data$output_type_id)
  data$value <- as.numeric(data$value)
  if (anyNA(data) || any(data$reference_date != reference_date)) {
    stop("Component forecasts contain missing values or incorrect reference dates")
  }
  hubUtils::as_model_out_tbl(data)
}

run_ensemble <- function(reference_date, overwrite) {
  path <- output_path(ensemble_id, reference_date)
  if (file.exists(path) && !overwrite) {
    message("Already exists, skipping ", path, " (use --overwrite to regenerate)")
    return(invisible(NULL))
  }
  components <- load_components(reference_date)
  ensemble <- hubEnsembles::simple_ensemble(
    components, agg_fun = mean, model_id = ensemble_id,
    task_id_cols = c("reference_date", "target", "horizon",
                     "target_end_date", "location")
  )
  submission <- dplyr::select(ensemble, dplyr::all_of(c(
    "reference_date", "target", "horizon", "target_end_date",
    "location", "output_type", "output_type_id", "value"
  )))
  check_submission(submission, reference_date,
                   allowed_horizons = -1:3)
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  write.csv(submission, path, row.names = FALSE)
  validation <- hubValidations::validate_submission(
    hub_path = ".", file_path = file.path(ensemble_id, basename(path)),
    skip_submit_window_check = TRUE
  )
  hubValidations::check_for_errors(validation, verbose = TRUE)
  message("Wrote and validated ", path)
}

if (sys.nframe() == 0L) {
  if (!file.exists("hub-config/tasks.json")) {
    stop("Run this script from the repository root")
  }
  packages <- c("hubUtils", "hubEnsembles", "hubValidations", "dplyr")
  missing_packages <- packages[!vapply(packages, requireNamespace,
                                       logical(1), quietly = TRUE)]
  if (length(missing_packages) > 0L) {
    stop("Install required R packages: ", paste(missing_packages, collapse = ", "))
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
    message("No 2026-27 ensemble round to backfill this Monday")
    quit(status = 0L)
  }
  for (date_string in as.character(seq(options$from, options$to, by = "7 days"))) {
    run_ensemble(as.Date(date_string), options$overwrite)
  }
}
