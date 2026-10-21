# CAT II submission checklist

The course rubric is treated as academic task context. It does not grant authorization to create accounts, spend money, publish to a cloud account, or contact others.

| Component | Included evidence | Status |
|---|---|---|
| Data engineering (8 marks) | NASA MAT files, cached downloader, checksums, actual schema, validation, causal features, battery-held-out split, PCA, plots | Implemented and executed |
| Advanced modeling (10 marks) | XGBoost, LSTM, GRU, Optuna studies, early stopping, scheduling, JSONL experiment tracking | Implemented and executed |
| Comparative analysis (10 marks) | Linear / forest / boosting / recurrent / persistence benchmarks, external lag-linear adaptation, error slices | Implemented and executed |
| Local deployment (4 marks) | Streamlit and FastAPI, validated inputs, saved-model loading, automated tests | Executed locally |
| Docker and cloud (4 marks) | Dockerfile, non-root runtime, CodeBuild tests, private ECR image and healthy ECS Fargate service | Verified on AWS: http://3.238.69.149:7860 |
| Report (4 marks) | IEEE-style two-column PDF, references, results, limitations | Included |

Before submission:

1. Final report with student details: `report/BatteryTwin_IEEE_Project_Report_SriRam_Sasi.pdf` (8 pages including cover).
2. Public source: https://github.com/sasi835/batterytwin.
3. Include the CodeBuild build/inference evidence and ECR image digest; local Docker Desktop is optional.
4. Include the verified public URL: http://3.238.69.149:7860 (task public IP may change on replacement).
5. Include those verified links in the final submission. No cloud URL is fabricated here.

Do not describe this system as physical EV fault diagnosis. NASA laboratory single-cell data has no labeled physical faults. RUL is exploratory; only B0005 supplies observed-EOL training labels. SOH is next-cycle forecasting with prior measured capacity, not inference from instantaneous telemetry.

Reference extensions add independently implemented GRU charge tracking, Gaussian-process RUL, utilization planning and capacity-derived health diagnostics. There are 25 analytical plots, 37 passing application tests plus eight deployment guard tests and an eight-page final report including cover. Charge tracking estimates a derived proxy, not measured vehicle SOC. Gaussian nominal 90% ranges cover only 26.25% of test observations. Life Planning does not validate intervention-based lifetime gains. The requirements audit inventories evidence without awarding marks. The local Docker engine is unavailable; Docker build/run and public dashboard inference have been verified on AWS. See artifacts/results/aws_ecr_deployment.json.

Final submission index: [SUBMISSION.md](../SUBMISSION.md). Primary live application: https://batterytwin.vercel.app.
