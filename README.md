# [AI4Casting Hub – Respiratory Virus Detection Surveillance System (RVDSS) Data Forecasting (2026-2027)](https://4castinghub.uoguelph.ca/respiratory-virus-detections/)
Welcome to the AI4Casting Hub's repository for the 2026-2027 Respiratory Virus Detection Surveillance System (RVDSS) Forecasting Challenge. This repository is dedicated to collecting weekly forecast data on respiratory virus detections across Canada. The challenge focuses on predicting the spread and detection of key respiratory viruses such as influenza, RSV, and COVID-19. Canadian respiratory virus surveillance report collects data from a network of laboratories across Canada, providing a valuable source of surveillance data to guide public health decisions.

[**Link to AI4Casting Hub's RVDSS Forecasting Official Page**](https://4castinghub.uoguelph.ca/respiratory-virus-detections)

### Challenge Overview
The AI4Casting Hub is organizing a collaborative nowcasting and forecasting challenge for respiratory virus detections using RVDSS data. The first RVDSS data update is Friday, October 23, 2026, and the final forecast submission is Saturday, May 29, 2027. During this period, participating teams are asked to provide weekly probabilistic interval hindcasts, nowcasts and forecasts for respiratory virus detections, at national, provincial and regional levels.

### Forecasting Targets
This challenge focuses on three primary targets:
* **Percentage of Weekly COVID-19 Positive Lab Detections (pct wk covid lab det)**
* **Percentage of Weekly Influenza Positive Lab Detections (pct wk flu lab det)**
* **Percentage of Weekly RSV Positive Lab Detections (pct wk rsv lab det)**

Teams will be tasked with forecasting the percentage of positive lab detections for:
* The preceding week (horizon -1)
* The current week (horizon 0)
* The following three weeks (horizon 1,2,3)

These predictions will be evaluated against confirmed RVDSS surveillance data released by public health agencies across Canada. For detailed information regarding the forecasting targets refer [model-output/README.md](https://github.com/ai4castinghub/rvdss-forecast/tree/main/model-output/README.md) file.

### Key Dates
* **First data update**: Friday, October 23, 2026 (morning, America/Toronto)
* **First forecast reference date**: Saturday, October 24, 2026
* **Final forecast reference date**: Saturday, May 29, 2027
* **Weekly Submission Deadline**: Saturdays at 11:30 p.m. America/Toronto time. The Saturday is the forecast's `reference_date` and due date.

The reference week corresponds to the epidemiological week (EW) running from Sunday to Saturday. Teams are expected to submit forecasts for the end of the reference week and the following three weeks. While teams are encouraged to forecast for all targets and time horizons, it is not required to submit predictions for every time period or virus. Forecasts for the previous week’s virus detections (horizon -1) are optional and will not be included in the primary scoring but may be helpful for calibration.

The hub's own four `epipredict` model outputs are generated as retrospective backfills on Mondays at 10:30 a.m. Toronto time for the preceding Saturday. See the [forecast script instructions](scripts/README.md). This does not extend the deadline for team submissions.

### Important Notes
RVDSS dashboard data for the preceding week is updated on Friday mornings. The hub's data workflow checks for those updates on Fridays; teams should confirm the latest data are available before submitting.

The final round's three-week-ahead target ends on June 19, 2027, so target data collection and evaluation continue after the final submission date.

Forecasts for a horizon of -1 (the previous week) are optional and will not be factored into official evaluations.

Each forecast will be evaluated using probabilistic metrics, comparing the submitted forecasts to actual reported RVDSS surveillance data.

### Scoring and Evaluation
Teams' forecasts will be scored using standard probabilistic forecasting metrics, such as the weighted interval score (WIS) and prediction interval coverage. While it is not mandatory to submit forecasts for all horizons or targets, submitting predictions for more targets and horizons is encouraged for comprehensive evaluation.

### Acknowledgments
This repository adheres to the hubverse guidelines and standards, leveraging open-source tools and data formats to facilitate collaboration among modeling teams. AI4Casting Hub acknowledges the support and contributions from public health agencies and participating laboratories in the RVDSS network.

---
**Contact**:  
For additional details or inquiries, please reach out to **Siddhesh S. Kadam** at [4castinghub@uoguelph.ca](mailto:4castinghub@uoguelph.ca).
