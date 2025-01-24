library(lubridate)
library(dplyr)
library(readr)
library(tidyr)
library(MMWRweek)

# Define the model output directory and reference date
model_output_dir <- "model-output"
current_reference_date <- floor_date(Sys.Date(), unit = "week") + days(6)

# Function to process individual model files
process_model_file <- function(file, model_name) {
  read_csv(file, show_col_types = FALSE) %>%
    mutate(
      model = model_name,
      reference_date = coalesce(
        as_date(dmy(reference_date)),
        as_date(as.numeric(reference_date), origin = "1970-01-01")
      ),
      target_end_date = coalesce(
        as_date(dmy(target_end_date)),
        as_date(as.numeric(target_end_date), origin = "1970-01-01")
      )
    ) %>%
    filter(!is.na(reference_date), !is.na(target_end_date))
}

# Function to process all files in a model directory
process_model_dir <- function(model_dir) {
  model_name <- basename(model_dir)
  model_files <- list.files(model_dir, pattern = "\\.csv$", full.names = TRUE)
  
  if (length(model_files) == 0) {
    message("No CSV files found in model directory: ", model_dir)
    return(NULL)
  }
  
  bind_rows(lapply(model_files, process_model_file, model_name = model_name))
}

# Process all model directories and combine data
all_model_data <- bind_rows(
  lapply(list.dirs(model_output_dir, full.names = TRUE, recursive = FALSE), process_model_dir)
)

# Save the combined data to a CSV file
write_csv(all_model_data, "auxiliary-data/concatenated_model_output.csv")