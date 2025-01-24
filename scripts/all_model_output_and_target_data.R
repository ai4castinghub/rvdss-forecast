library(lubridate)
library(dplyr)
library(readr)
library(tidyr)
library(MMWRweek)

# Initialize an empty list to hold data frames
all_data <- list()

required_columns <- c("sarscov2_pct_positive", "rsv_pct_positive", "flu_pct_positive")

# Loop through the seasons
for (year in 2019:2024) {
  season_folder <- paste0("auxiliary-data/target-data-archive/season_", year, "_", year + 1)
  file_path <- file.path(season_folder, "target_rvdss_data.csv")
  
  if (file.exists(file_path)) {
    # Read the CSV file
    data <- read.csv(file_path, stringsAsFactors = FALSE)
    
    missing_columns <- setdiff(required_columns, colnames(data))
    
    if (length(missing_columns) > 0) {
      for (col in missing_columns) {
        data[[col]] <- NA
      }
    }
    
    # Add a season column for reference
    data$Season <- paste0(year, "-", year + 1)
    
    # Append the data to the list
    all_data[[length(all_data) + 1]] <- data
  } else {
    warning(paste("File not found:", file_path))
    data <- read.csv('target-data/season_2024_2025/target_rvdss_data.csv', stringsAsFactors = FALSE)
    
    # Add a season column for reference
    data$Season <- paste0(year, "-", year + 1)
    
    # Append the data to the list
    all_data[[length(all_data) + 1]] <- data
    print("File found at: target-data/season_2024_2025/target_rvdss_data.csv")
    
  }
}

# Combine all data frames, ensuring all columns are included
final_data <- bind_rows(all_data)

# Write the combined data to a new CSV file
write.csv(final_data, "auxiliary-data/concatenated_rvdss_data.csv", row.names = FALSE)

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