# BatteryTwin rubric evidence

The primary interface is Streamlit. The public deployment package uses Docker SDK metadata, a Python 3.12 image, a non-root user, saved-artifact startup checks, and port 7860. The original FastAPI interface remains available for the local API demonstration.

| Evaluation component | Marks available | Concrete evidence | Current state |
|---|---:|---|---|
| Data engineering and visualization | 8 | NASA source manifest, validation, 15 causal features, battery-wise splits, train-only preprocessing, PCA, 25 analytical plots and SHAP | Implemented and executed |
| Advanced modeling and pipeline optimization | 10 | XGBoost, LSTM/GRU, Gaussian RUL, modular training, Optuna studies, early stopping and JSONL experiment logs | Implemented and executed |
| Benchmarking and comparative analysis | 10 | Common held-out targets, persistence and lag-linear baselines, external source comparison, MAE/RMSE/R-squared, residual and condition-based errors | Implemented and executed; no state-of-the-art superiority claim |
| Local inference application | 4 | Streamlit measurement forms and replay, validated shared service, retained FastAPI, nine Streamlit tests plus 28 data/API tests | Verified locally |
| Docker and public cloud | 4 | Dockerfile, CodeBuild Docker build/inference checks, private ECR image, healthy ECS Fargate service and live browser evidence | Verified on AWS: http://3.238.69.149:7860; Hugging Face runtime blocked separately |
| Documentation and report quality | 4 | README, modular code, notebooks, deployment guide, reference comparison, seven-page academic report, separate local lab record | Included; public source Space and live AWS app available |

These are evidence descriptions, not awarded marks. The instructor determines the final score.

## Run locally

```powershell
.\start-streamlit.ps1
```

The Streamlit interface uses http://127.0.0.1:8501. To demonstrate the original FastAPI application, run `./start.ps1` and open http://127.0.0.1:8000/docs.

## Container and cloud verification

```powershell
.\deploy-docker.ps1
```

This builds the Streamlit image, waits for container readiness and executes saved-model prediction inside the container. A working Docker Desktop Linux engine is required. The latest startup attempt failed on Docker's inaccessible temporary `sailor-ingest.sock`; local execution remains blocked. The same image was built and tested remotely in CodeBuild and runs on ECS.

The user approved deploying to existing public Space `sasi468896/aml_cat`. The current login is `sasi468896`; upload succeeded on October 15, 2026, with 109 files at commit `ab5ba052e5779c10652fb32747324213a5895f23`. The SDK is Docker. Runtime is CONFIG_ERROR because the existing ZeroGPU hardware only supports Gradio. Switching to CPU Basic returned HTTP 402 requiring PRO. No subscription or billing change was made. The instructor should not treat the uploaded source as a running cloud deployment.

The Space staging script publishes only the standalone BatteryTwin academic report. The complete personal lab record, its cover and the student's registration details are excluded.

AWS deployment verified October 15, 2026: [BatteryTwin](http://3.238.69.149:7860). ECR image digest, healthy ECS task, container inference output, browser capacity-edit check and screenshots are recorded in `artifacts/results/aws_ecr_deployment.json`.
