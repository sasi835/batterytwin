# Adaptation of the supplied EV battery reference

Inspected repository: [AI-Based Predictive Diagnosis and Lifetime Optimization for EVs Battery](https://github.com/ahmedmhb/AI-Based-Pedictive-Diagnosis-and-Lifetime-Optimization-for-EVs-Battery/tree/72fa7bff18b91b0b1c602c5cb3fadbbee51ef0a8). Pinned revision: `72fa7bff18b91b0b1c602c5cb3fadbbee51ef0a8`.

The user requested this repository as a reference. Course requirements are treated as project context, not as permission to publish to an unspecified account. BatteryTwin uses independent implementations and its existing NASA data; source code, models and vehicle data from the reference are not redistributed. No license file was found in the inspected tree.

| Reference idea and inspected source | BatteryTwin implementation | Difference and evidence |
|---|---|---|
| Vehicle SOC with GRU (`soc.py`, `claude/pipeline.py`) | `src/data/discharge.py`, saved charge Random Forest and GRU; `/predict/soc`; Charge Tracking view | NASA has no measured SOC. Target is a coulomb-count discharge-relative charge proxy, assuming a full start. Completed-cycle capacity is an offline target denominator only; online inputs are past/current V/I/T/time. Integration precedes downsampling. |
| Charging-event GRU SOH (`soh.py`) | Existing PyTorch GRU and LSTM next-cycle SOH benchmarks | Forecasts completed-discharge capacity using prior measured cycles. This differs from vehicle charging-event SOH. |
| Matérn Gaussian-process RUL (`rul.py`) | `src/models/gaussian_rul.py`, `models/rul_gpr.pkl`, RUL API comparison | Fits observed NASA EOL crossing labels; does not generate Wiener pseudo-ground-truth. Uses train-only imputation/scaling and battery-held-out evaluation. |
| RUL ranges (`rul_system.py`) | Actual Gaussian posterior predictive standard deviations and nominal 90% ranges | No heuristic percentage is presented as calibrated confidence. Held-out coverage is **26.25%**, indicating severe undercoverage; the range is not a fleet guarantee. Zero follows any observed EOL crossing. |
| Lifetime optimization theme | `src/models/planning.py`, `/plan/lifetime`, Life Planning view | Transparent utilization arithmetic holds remaining cycle life fixed. No training data validates intervention benefits, optimal charge settings or lifetime improvement. |
| Vehicle-based validation (`claude/pipeline.py`) | B0005+B0007 training, B0018 validation, B0006 testing | Four NASA laboratory cells differ from the source vehicle population. No source-score superiority or exact protocol reproduction is claimed. |
| Operational checks (`soh_test.py`, `test_rul.py`) | Existing and extension tests: causal inputs, ordered traces, boundary validation, capacity sensitivity, EOL persistence, API readiness | Physical monotonicity is not forced on genuine capacity-recovery observations. |

The inspected pipeline describes BAIC EU500 CATL NCM 145 Ah vehicle data. Its scripts use differing EOL definitions (80% in `claude/pipeline.py`, 65% in `rul.py`) and target construction. BatteryTwin retains NASA's documented 70% of 2 Ah threshold. These datasets, units, target definitions and splits prevent direct comparison of reported scores.

## Executed extension results

Gaussian RUL: MAE 11.201 cycles, RMSE 13.172, R² 0.845 on the same 160 held-out target cycles. The existing RUL forest is stronger (MAE 6.429). The Gaussian fit reached some kernel bounds; this is retained as a modeling limitation rather than hidden.

Derived-charge evaluation: 2,748 common sequence-eligible B0006 sensor samples. Forest MAE 3.021 percentage points and RMSE 6.033; GRU MAE 3.962 and RMSE 5.001. These quantify agreement with a **derived** reference, not independent BMS SOC accuracy. Adjacent samples are correlated. Scaling uses training batteries only, and recurrent windows stay within a single discharge.

The health confusion matrix and ROC/PR plots evaluate capacity-derived health categories using next-cycle predicted SOH. They do not evaluate labeled physical faults or turn Isolation Forest scores into fault probabilities. Health thresholds remain project conventions.

Reproduce with `python scripts/reference_extensions.py` after the core training workflow. Evidence: `artifacts/results/gaussian_rul.json`, `soc_benchmark.json`, `health_classification.json`, `benchmark.csv`, the seven additional plots and durable experiment logs. Public GitHub and deployment links are still required for final submission.
