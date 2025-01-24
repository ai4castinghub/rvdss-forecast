import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")


# Load the model data
model_data = pd.read_csv('auxiliary-data/concatenated_model_output.csv')

# Load the truth data
truth_data = pd.read_csv('target-data/season_2024_2025/target_rvdss_data.csv')
truth_data = truth_data.rename(columns={"time_value": "time"})
truth_data['time'] = pd.to_datetime(truth_data['time']).dt.date

# Ensure model data types are correct
model_data['reference_date'] = pd.to_datetime(model_data['reference_date']).dt.date
model_data['target_end_date'] = pd.to_datetime(model_data['target_end_date']).dt.date
model_data['output_type_id'] = pd.to_numeric(model_data['output_type_id'], errors='coerce')

print(model_data)
print(truth_data)
# Calculate reference date
current_date = datetime.now().date()
ref_date = current_date + timedelta(days=(6 - current_date.weekday())) - timedelta(days=1, weeks=1)

# Filter model data for the reference date
model_data = model_data[model_data['reference_date'] == ref_date]

locations = pd.read_csv('auxiliary-data/locations.csv')

# Group by region (location)
targets = model_data['target'].unique()
file_name = 'weekly-forecast-reports/' + str(ref_date)+"-Forecast_Report.pdf"
# Open a PDF to save the plots
with PdfPages(file_name) as pdf:
    # Iterate over each target
    for target in targets:
        target_data = model_data[model_data['target'] == target]
        regions = target_data['location'].unique()

        # Reorder regions: Ontario first, then alphabetical for the rest
        regions = sorted([region for region in regions if region != "ca"])
        if "ca" in target_data['location'].unique():
            regions = ["ca"] + regions

        # Match target to truth data columns (e.g., covid, flu, rsv)
        truth_column = (
            "sarscov2_pct_positive" if "covid lab" in target.lower() else
            "flu_pct_positive" if "flu lab" in target.lower() else
            "rsv_pct_positive" if "rsv lab" in target.lower() else
            None
        )
        
        if truth_column is None:
            print(f"Skipping target '{target}' as it doesn't match truth data columns.")
            continue

        for region in regions:
            region_data = target_data[target_data['location'] == region]
            
            if region_data.empty:
                print(f"No data for region: {region}, target: {target}")
                continue  # Skip if no data for this region
            
            # Create figure with two subplots
            fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)

            ref_yaxis = region_data[region_data['output_type_id'] == 0.5]

            # Helper function to calculate intervals
            def calculate_intervals(data):
                return data.groupby('target_end_date').apply(
                    lambda x: pd.Series({
                        'median': x.loc[x['output_type_id'] == 0.5, 'value'].mean(),
                        'lower_95': x.loc[x['output_type_id'] == 0.025, 'value'].mean(),
                        'upper_95': x.loc[x['output_type_id'] == 0.975, 'value'].mean(),
                        'lower_50': x.loc[x['output_type_id'] == 0.25, 'value'].mean(),
                        'upper_50': x.loc[x['output_type_id'] == 0.75, 'value'].mean(),
                    })
                ).reset_index()

            # Left Plot: All Models (excluding ensemble)
            ax = axes[0]
            ax.set_ylim([ref_yaxis['value'].min()/2, ref_yaxis['value'].max() * 2])
            non_ensemble_data = region_data[region_data['model'] != 'AI4Casting_Hub-Ensemble_v1']
            for model in non_ensemble_data['model'].unique():
                model_specific_data = non_ensemble_data[non_ensemble_data['model'] == model]
                
                if model_specific_data.empty:
                    print(f"No data for model: {model}, region: {region}, target: {target}")
                    continue
                
                # Calculate intervals
                grouped = calculate_intervals(model_specific_data)
                
                # Plot the median and confidence intervals
                if not grouped.empty:
                    line, = ax.plot(grouped['target_end_date'], grouped['median'], label=f"{model}")
                    ax.fill_between(
                        grouped['target_end_date'],
                        grouped['lower_95'],
                        grouped['upper_95'],
                        alpha=0.2,
                        color=line.get_color(),
                        label='_nolegend_'
                    )
                    # ax.fill_between(
                    #     grouped['target_end_date'],
                    #     grouped['lower_50'],
                    #     grouped['upper_50'],
                    #     alpha=0.2,
                    #     color=line.get_color(),
                    #     label='_nolegend_'
                    # )
                    ax.scatter(
                        grouped['target_end_date'],
                        grouped['median'],
                        color=line.get_color(),
                        alpha=1,
                        s=30  # Size of the dots
                    )
                else:
                    print(f"No grouped data for model: {model}, region: {region}, target: {target}")
            
            # Add truth data to the left plot
            region_truth = truth_data[truth_data['geo_value'] == region]
            region_truth = region_truth.sort_values(by='time')

            if not region_truth.empty and truth_column in region_truth.columns:
                ax.plot(
                    region_truth['time'],
                    region_truth[truth_column],
                    label="Truth Data",
                    color="black",
                    linestyle="--",
                    linewidth=2
                )
            else:
                print(f"No truth data for region: {region}")

            full_region_name = locations[locations['geo_abbr']==region]['geo_name'].values[0]
            ax.set_title(f"Forecasting Models - {full_region_name} - {target}")
            ax.set_xlabel("Target End Date")
            ax.set_ylabel("Forecast Value")
            ax.legend(loc="upper left", fontsize="small")
            ax.grid()

            # Right Plot: Truth Data + Ensemble Model
            ax = axes[1]
            ensemble_data = region_data[region_data['model'] == 'AI4Casting_Hub-Ensemble_v1']
            if not ensemble_data.empty:
                grouped = calculate_intervals(ensemble_data)
                
                if not grouped.empty:
                    line, = ax.plot(grouped['target_end_date'], grouped['median'], label="Ensemble")
                    ax.fill_between(
                        grouped['target_end_date'],
                        grouped['lower_95'],
                        grouped['upper_95'],
                        alpha=0.1,
                        color=line.get_color(),
                        label='_nolegend_'
                    )
                    ax.fill_between(
                        grouped['target_end_date'],
                        grouped['lower_50'],
                        grouped['upper_50'],
                        alpha=0.2,
                        color=line.get_color(),
                        label='_nolegend_'
                    )
                    ax.scatter(
                        grouped['target_end_date'],
                        grouped['median'],
                        color=line.get_color(),
                        s=20  # Size of the dots
                    )
            
            # Add truth data to the right plot
            if not region_truth.empty and truth_column in region_truth.columns:
                ax.plot(
                    region_truth['time'],
                    region_truth[truth_column],
                    label="Truth Data",
                    color="black",
                    linestyle="--",
                    linewidth=2
                )
            else:
                print(f"No truth data for region: {region}")

            ax.set_title(f"Ensemble Model - {full_region_name} - {target}")
            ax.set_xlabel("Target End Date")
            ax.legend(loc="upper left", fontsize="small")
            ax.grid()

            # Adjust layout and save the figure
            plt.tight_layout()
            pdf.savefig()
            plt.close()

print("Plots saved!")
