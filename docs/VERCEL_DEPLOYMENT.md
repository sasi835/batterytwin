# BatteryTwin on Vercel

The Vercel target uses **Container Runtime beta**, which builds `Dockerfile.vercel` and runs the full Streamlit application. It is not a static landing page or a redirect to AWS. The Vercel-specific Dockerfile uses the same application, model artifacts and dependencies as the Docker image already tested on AWS. `vercel.json` sets the HTTP port to 7860 and limits numerical-library worker threads.

Official sources: [Container Runtime](https://vercel.com/docs/functions/runtimes/container), [WebSockets](https://vercel.com/docs/functions/websockets), [function limits](https://vercel.com/docs/functions/limitations), [CLI deployment](https://vercel.com/docs/cli/deploy).

## Prepare

```powershell
.\.venv\Scripts\python.exe scripts/prepare_vercel.py
```

This creates `output/vercel/batterytwin` with an explicit runtime allowlist, saved models, processed NASA data, analytical results, and the standalone academic report. Credentials, raw data, the personal lab record, local logs and screenshots are excluded. Review `artifacts/results/vercel_manifest.json`.

## Sign in and deploy

From the project root, use the official CLI:

```powershell
npm.cmd exec --cache ./tmp/npm-cache --yes --package vercel@latest -- vercel login
npm.cmd exec --cache ./tmp/npm-cache --yes --package vercel@latest -- vercel whoami
npm.cmd exec --cache ./tmp/npm-cache --yes --package vercel@latest -- vercel deploy ./output/vercel/batterytwin --prod --yes --env PORT=7860
```

Use the intended personal account/team and review any plan or billing prompts. No paid plan upgrade is authorized by these instructions. No AWS or Hugging Face token is needed. Keep credentials out of chat and source files.

The official runtime automatically detects `Dockerfile.vercel`, builds the image remotely and routes requests to it. Local Docker is only needed for local `vercel dev`, not the hosted build. If the account cannot use Container Runtime beta or the deployment exceeds platform limits, resolve that specific error before claiming success.

## Verify the actual deployment

Use the URL returned by Vercel, verify `/_stcore/health`, open the Dashboard and submit a capacity measurement on Predictions. A READY deployment alone is not enough: Streamlit needs an operational WebSocket session. Record build logs, health, prediction output and screenshot evidence in `artifacts/results/vercel_deployment.json` only after verification.

Vercel Functions have duration and memory limits. Hobby currently has 2 GB memory and a 300-second maximum request duration; a long Streamlit session may reconnect and lose transient in-memory UI state. Containers can scale down when idle and will load artifacts again on a cold start. Do not claim unlimited persistent sessions. The beta may impose additional account-specific requirements.

The existing AWS ECS service remains separate and continues incurring its approved charges. Moving to Vercel does not stop or delete AWS resources. Current Vercel status: deployed and verified at https://batterytwin.vercel.app. Container build succeeded, public health returned 200/ok, and a browser prediction using 1.60 Ah returned 80.3% next-cycle SOH and approximately 52 remaining cycles.


## Verified publication

GitHub: https://github.com/sasi835/batterytwin (private, main). Production: https://batterytwin.vercel.app. Deployment ID: `dpl_FcXydmZWeSyQ9V126krvDfXvT2CB`. The deployed application source revision is `5b1923f5137db48209f70012987561f6b31d147a`; later commits add publication evidence and screenshots. The Vercel build reported Container Runtime and stored the image in VCR. Its OCI builder ignores Docker HEALTHCHECK instructions, so deployment health was verified through the public Streamlit endpoint and actual browser inference.

The deployment used the authenticated CLI. Vercel could not connect its GitHub integration to the private repository, so pushing future commits does not automatically redeploy. To enable that, grant the intended Vercel GitHub integration access to this specific private repository in your account, then connect it through the project Git settings. Alternatively, regenerate the staged package and redeploy with the CLI commands above. No repository visibility or GitHub access permissions were changed.
