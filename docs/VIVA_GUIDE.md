# BatteryTwin presentation and viva guide

## Suggested 8-minute demonstration

1. Explain the task: next-cycle capacity-based health forecasting, exploratory RUL and unlabeled anomaly detection.
2. Show four real NASA batteries and move the completed-cycle slider. Explain that this replays recorded measurements.
3. Distinguish measured SOH (capacity / 2 Ah) from the next-cycle model forecast.
4. Open Model Performance. State directly that persistence and a two-lag linear adaptation outperform the advanced SOH models.
5. Open Analytics: explain causal features, training-only PCA, Optuna objectives, recurrent loss and SHAP.
6. Open RUL Prediction: explain first observed 70% crossing, censored B0007 and the single uncensored training cell.
7. Open Anomaly Detection: describe validation-percentile novelty thresholds, not physical faults.
8. Open API docs and explain saved-model loading, input validation, tests and Docker/cloud readiness. Show a live cloud URL only after actual deployment.

## Likely questions

**Why do complex models lose?** Four cells provide a small training population. Next-cycle capacity changes are often small; previous measured capacity already provides a strong prediction. High model complexity and operating-condition differences can hurt generalization. The observed scores support this explanation but do not identify a unique causal reason.

**Why use rated capacity rather than first capacity?** NASA specifies a 2 Ah rated reference and 1.4 Ah EOL criterion. Using 2 Ah keeps SOH and EOL definitions consistent. A first-cycle reference would yield different percentages and crossings.

**Is prior capacity target leakage?** In a one-step task, previous completed-cycle capacity is available before forecasting the next cycle. Current/target-cycle capacity is excluded from features. In an open-loop forecast with no new measurements, this input would not remain available; the project does not claim that formulation.

**Why battery-wise splitting?** Randomly mixing cycles from the same cell can exploit correlated trajectories and overstate cross-cell generalization. Here training, validation and test cells are disjoint. Only one test cell remains, which is a limitation.

**Why choose Random Forest if persistence wins?** The API demonstrates the learned model selected by tabular validation MAE; it is not advertised as the best test forecast. Persistence remains an explicit benchmark. The external lag-linear adaptation is a post-training comparative experiment, not a retrospective deployment selection.

**Why no anomaly confusion matrix or F1?** There are no labeled physical faults. Reporting supervised classification metrics would require inventing labels. The scores are distribution novelty, calibrated by validation percentiles.

**How is RUL labeled?** First observed capacity <=1.4 Ah defines EOL. Remaining cycles are EOL index minus target index, floored at zero. B0007 has no observed EOL, so its RUL is unknown and excluded. The future threshold is used only for offline target construction.

**What is SHAP?** It decomposes the fitted tree prediction into a base value plus feature contributions. It explains model output and does not establish electrochemical causality.

**What happens if the model is missing?** The API remains available but readiness/inference returns 503. It never silently retrains or emits fabricated results.

**Was cloud deployment completed?** Local inference and dashboard were verified. Docker/Spaces/EC2 configuration is prepared. Public deployment remains pending until a target account is supplied and the build is actually verified.

**What would improve the study?** More cells, repeated held-out-cell splits, independently tuned GRU, longer-horizon recursive evaluation, censored survival RUL models, uncertainty calibration on independent cells and real EV telemetry.
