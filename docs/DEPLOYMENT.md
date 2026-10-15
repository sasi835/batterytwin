# BatteryTwin deployment

## Local Streamlit

Run `./start-streamlit.ps1` from the project folder and open http://127.0.0.1:8501. Saved models load at startup; training remains offline. The original FastAPI demonstration is available through `./start.ps1` at http://127.0.0.1:8000/docs.

## Docker

Start Docker Desktop with its Linux engine, then run:

```powershell
.\deploy-docker.ps1
```

The helper builds the Streamlit image, waits for health, and checks real saved-model inference inside the container. The default host port is 8501; `-Port 8502` selects another port. The container listens on 7860.

Manual alternative:

```powershell
docker build -t batterytwin .
docker run --rm -p 8501:7860 batterytwin
```

Open http://localhost:8501. The Python 3.12 image runs as a non-root user, bundles saved models and processed data, and checks `/_stcore/health`. It includes the standalone academic report; the personal lab record is excluded.

Current local limitation: Docker Desktop cannot start its Linux engine because its temporary `sailor-ingest.sock` is inaccessible (Windows error 1920). Container build/run remains unverified. Restart Windows and confirm Docker Desktop's engine is running before using the helper.

## Approved Hugging Face Space

Target: https://huggingface.co/spaces/sasi468896/aml_cat

The user approved replacing the existing empty Gradio setup with BatteryTwin Streamlit in Docker. The current login is `sasi468896`. Upload succeeded on October 15, 2026: 109 files, approximately 55.4 MiB, commit `ab5ba052e5779c10652fb32747324213a5895f23`.

Current blocker: runtime CONFIG_ERROR, "ZeroGPU is only available on Gradio SDK". Requesting CPU Basic returned HTTP 402: the account needs PRO to downgrade this Space. [Official hardware documentation](https://huggingface.co/docs/hub/spaces-gpus) states that CPU Basic has no hourly charge but compute Space creation requires a paid plan. The owner must resolve plan eligibility and select CPU Basic in Space settings. No billing or subscription change was made. The Docker build and live application remain unverified.

Sign in from your terminal using a token with write access to this Space. Do not put the token in chat or source files:

```powershell
hf auth login
hf auth whoami
.\.venv\Scripts\python.exe scripts/publish_space.py --repo sasi468896/aml_cat --update
```

Use the owning account `sasi468896`, or an account explicitly granted write access. Download access alone does not permit deployment.

The publisher verifies the existing Space and write permission, prepares an explicit runtime allowlist, then uploads it. The staged README selects Docker SDK and app port 7860. Credentials, raw data, local logs, temporary downloads and personal lab records are excluded. Inspect `artifacts/results/space_manifest.json` for the upload list.

After upload, inspect the Space build logs, wait for RUNNING, verify `/_stcore/health`, and open the dashboard to check model inference. A successful upload alone does not establish a successful deployment. The publisher records initial status in `artifacts/results/huggingface_deployment.json`; live verification is still required.


## AWS Lightsail alternative

See [AWS deployment](AWS_DEPLOYMENT.md). The prepared launcher uses the same Dockerfile and builds remotely, with a $24/month bundle cap, HTTP on port 80 and saved-model inference checks. Four deployment guard tests and bootstrap shell syntax passed; all 109 source files were verified at the pinned public revision. The Lightsail alternative was not launched. The approved ECR + ECS deployment is running at http://3.238.69.149:7860; see AWS_ECR_DEPLOYMENT.md.


## Verified AWS ECR and ECS deployment

[Open BatteryTwin](http://3.238.69.149:7860). CodeBuild built and tested the Docker image, ECR stores it privately, and ECS runs a healthy Fargate task. Public HTTP health, dashboard and edited-capacity inference passed. See [the ECR/ECS guide](AWS_ECR_DEPLOYMENT.md) for configuration, evidence and cleanup.
