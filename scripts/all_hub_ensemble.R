# Generate Simple_Ens and Team_Ens separately from the four epipredict models.
# Run from the repository root after refreshing the concatenated model output.
# Rscript scripts/all_hub_ensemble.R --reference-date 2026-11-14
source("scripts/hub_model_forecasts.R", local = TRUE)

simple_ensemble_id <- "AI4Casting_Hub-Simple_Ens"
team_ensemble_id <- "AI4Casting_Hub-Team_Ens"
excluded_models <- c(
  simple_ensemble_id,
  team_ensemble_id,
  "AI4Casting_Hub-Ensemble_v1",
  "AI4Casting_Hub-Quantile_Baseline",
  "AI4Casting_Hub-Flatline",
  "AI4Casting_GPT_4o",
  "AI4Casting_Hub-GPT_4o",
  "AI4Casting_Hub-Weighted_Ensemble"
)

eligible_team_models <- function(metadata_dir = "model-metadata") {
  if (!dir.exists(metadata_dir)) stop("Missing model metadata: ", metadata_dir)
  paths <- list.files(metadata_dir, pattern = "\\.ya?ml$", full.names = TRUE)
  # Hub-owned files cannot contribute, regardless of their metadata contents.
  paths <- paths[!startsWith(basename(paths), "AI4Casting_")]
  eligible <- vapply(paths, function(path) {
    metadata <- yaml::read_yaml(path, readLines.warn = FALSE)
    # External hub ensembles are eligible too; designated_model controls consent.
    isTRUE(metadata$designated_model) &&
      !metadata$team_abbr %in% c("AI4Casting_Hub", "AI4Casting") &&
      !metadata$team_name %in% c("AI4Casting_Hub", "AI4Casting Hub")
  }, logical(1))
  tools::file_path_sans_ext(basename(paths[eligible]))
}

load_components <- function(reference_date, ensemble_id = simple_ensemble_id) {
  path <- "auxiliary-data/concatenated_model_output.csv"
  if (!file.exists(path)) stop("Missing concatenated model output: ", path)
  data <- read.csv(path, stringsAsFactors = FALSE)
  columns <- c("reference_date", "target", "horizon", "target_end_date",
               "location", "output_type", "output_type_id", "value", "model")
  missing <- setdiff(columns, names(data))
  if (length(missing)) stop("Concatenated model output is missing: ",
                            paste(missing, collapse = ", "))
  keep <- data$reference_date == as.character(reference_date)
  if (ensemble_id == team_ensemble_id) {
    keep <- keep & data$model %in% eligible_team_models() & data$horizon %in% 0:3
  } else {
    keep <- keep & !data$model %in% excluded_models
  }
  data <- data[keep, columns, drop = FALSE]
  if (nrow(data) == 0L) {
    if (ensemble_id == team_ensemble_id) {
      message("No eligible team submissions at horizons 0-3 for ", reference_date,
              "; skipping ", ensemble_id)
      return(NULL)
    }
    stop("No component forecasts for ", reference_date)
  }
  message("Ensembling ", length(unique(data$model)), " models for ",
          ensemble_id, " on ", reference_date)
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

run_ensemble <- function(reference_date, overwrite, ensemble_id = simple_ensemble_id) {
  path <- output_path(ensemble_id, reference_date)
  if (file.exists(path) && !overwrite) {
    message("Already exists, skipping ", path, " (use --overwrite to regenerate)")
    return(invisible(NULL))
  }
  components <- load_components(reference_date, ensemble_id)
  if (is.null(components)) return(invisible(NULL))
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
                   allowed_horizons = if (ensemble_id == team_ensemble_id) 0:3 else -1:3)
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
  packages <- c("hubUtils", "hubEnsembles", "hubValidations", "dplyr", "yaml")
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
    run_ensemble(as.Date(date_string), options$overwrite, team_ensemble_id)
  }
}
