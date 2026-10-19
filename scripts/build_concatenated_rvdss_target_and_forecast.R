library(lubridate)
library(dplyr)
library(readr)

# required columns that must exist in all rvdss files
required_columns <- c("sarscov2_pct_positive", "rsv_pct_positive", "flu_pct_positive")

# helper to load a single season and ensure required columns
load_season_data <- function(year) {
  season_folder <- if (year <= 2024) {
    paste0("auxiliary-data/target-data-archive/season_", year, "_", year + 1)
  } else {
    paste0("target-data/season_", year, "_", year + 1)
  }
  file_path     <- file.path(season_folder, "target_rvdss_data.csv")
  
  if (!file.exists(file_path)) {
    warning("file not found: ", file_path)
    return(NULL)
  }
  
  # read data
  data <- read_csv(file_path, show_col_types = FALSE)
  
  # add any missing required columns as na
  missing_columns <- setdiff(required_columns, colnames(data))
  if (length(missing_columns) > 0) {
    for (col in missing_columns) {
      data[[col]] <- NA_real_
    }
  }
  
  # add season label
  data$Season <- paste0(year, "-", year + 1)
  
  data
}

# load all seasons and combine
all_data <- lapply(2019:2026, load_season_data)
final_data <- bind_rows(all_data) %>%
  mutate(geo_value = if_else(geo_value == "yk", "yt", geo_value))

# write concatenated rvdss data
write_csv(final_data, "auxiliary-data/concatenated_rvdss_data.csv")

# model output directory and reference date used for filtering
model_output_dir <- "model-output"
current_reference_date <- ref_date <- ceiling_date(Sys.Date(), "week") - days(1) - weeks(1) #floor_date(Sys.Date(), unit = "week") + days(6)
current_reference_date

# helper to process individual model files
process_model_file <- function(file, model_name) {
  read_csv(file, show_col_types = FALSE) %>%
    mutate(
      model = model_name,
      reference_date = coalesce(
        as_date(ymd(reference_date)),
        as_date(dmy(reference_date)),
        as_date(as.numeric(reference_date), origin = "1970-01-01")
      ),
      target_end_date = coalesce(
        as_date(ymd(target_end_date)),
        as_date(dmy(target_end_date)),
        as_date(as.numeric(target_end_date), origin = "1970-01-01")
      )
    ) %>%
    filter(!is.na(reference_date), !is.na(target_end_date))
}

# helper to process all files in a model directory
process_model_dir <- function(model_dir) {
  model_name  <- basename(model_dir)
  model_files <- list.files(model_dir, pattern = "\\.csv$", full.names = TRUE)
  
  if (length(model_files) == 0) {
    message("no csv files found in model directory: ", model_dir)
    return(NULL)
  }
  
  bind_rows(lapply(model_files, process_model_file, model_name = model_name))
}

# process all model directories and combine
model_dirs <- list.dirs(model_output_dir, full.names = TRUE, recursive = FALSE)
all_model_data <- bind_rows(lapply(model_dirs, process_model_dir))

# clean values and filter by cutoff date
cutoff_date <- as_date("2026-10-24")

all_model_data <- all_model_data %>%
  mutate(value = if_else(value < 0, 0, round(value, 2))) %>%
  filter(reference_date >= cutoff_date)

# write concatenated model output
write_csv(all_model_data, "auxiliary-data/concatenated_model_output.csv")
