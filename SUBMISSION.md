# BatteryTwin — CAT II submission

**SriRam Sasi M · 2403717674421052 · M.Sc. AIML**  
Coimbatore Institute of Technology · Advanced Machine Learning Lab (19MAM56)

- Public source: https://github.com/sasi835/batterytwin
- Live Streamlit application: https://batterytwin.vercel.app
- AWS application: http://3.238.69.149:7860 (task address may change).
- [Final PDF: 8 pages including institutional cover](report/BatteryTwin_IEEE_Project_Report_SriRam_Sasi.pdf)
- [Editable Word report](report/BatteryTwin_IEEE_Project_Report_SriRam_Sasi.docx)

| Deliverable | Location |
|---|---|
| Modular Python code and notebooks | `src/`, `api/`, `scripts/`, `streamlit_app.py`, `notebooks/` |
| Dependencies and model configuration | `requirements*.txt`, `configs/config.yaml`, `models/*schema.json` |
| Container files | `Dockerfile`, `Dockerfile.vercel`, `docker-compose.yml` |
| Models and processed data | `models/`, `data/processed/`, provenance in `data/raw/manifest.json` |
| Visualization, metrics and experiments | `artifacts/`, `docs/RUBRIC_EVIDENCE.md` |
| Report within 10-page limit | `report/`: 8-page PDF and editable Word |
| Cloud evidence | `artifacts/results/vercel_deployment.json`, `artifacts/results/aws_ecr_deployment.json` |

## Run locally

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-streamlit.txt
./start-streamlit.ps1
```

Open http://127.0.0.1:8501. Docker: `docker compose up --build`, then open the same address. README.md provides training and evaluation instructions.

Saved models forecast next-cycle health from prior completed cycles. NASA single-cell experiments do not establish EV pack fault diagnosis. The main benchmark's persistence baseline outperforms the learned SOH models. Hugging Face source is uploaded, but its runtime is blocked by hardware/plan settings; use Vercel for evaluation. Cloud evidence records its verification dates.

The ZIP excludes credentials, environments, raw downloads, staging folders and unrelated personal lab records. Create it with `python scripts/package_project.py` after staging intended Git files.
