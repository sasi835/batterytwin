# BatteryTwin Docker deployment on AWS

The user now requests Amazon ECR. See [the current ECR + ECS deployment guide](AWS_ECR_DEPLOYMENT.md). This Lightsail setup is an unused alternative; it has not been launched.

This setup runs the existing Streamlit Docker image on an Ubuntu 24.04 Amazon Lightsail instance. The image builds on AWS, so local Docker Desktop is optional. The server downloads the approved public runtime files from immutable Hugging Face commit `ab5ba052e5779c10652fb32747324213a5895f23`; no AWS or Hugging Face credentials are sent to it. Personal lab records are excluded.

## Configuration and cost

- Region: `us-east-1`, matching the current AWS CLI configuration.
- Instance: `batterytwin-streamlit`, Linux, 4 GB RAM, at least 2 vCPUs, public IPv4.
- Expected bundle: $24/month, billed hourly up to the monthly bundle price. The launcher checks current AWS bundle prices and refuses a bundle above its $24 cap.
- Port 80 serves the Streamlit demo over HTTP. SSH is restricted to AWS browser SSH address ranges. The container runs as a non-root user, restarts after reboot, and rotates logs.
- No paid load balancer, GPU, managed database, automatic snapshots or additional static IP is provisioned. Taxes and excess data transfer may add charges; account credits/free-tier eligibility are not assumed.

Sources: [AWS instance bundles and pricing](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html), [instance creation](https://docs.aws.amazon.com/cli/latest/reference/lightsail/create-instances.html), [firewall API](https://docs.aws.amazon.com/cli/latest/reference/lightsail/put-instance-public-ports.html).

## Prepare and review

```powershell
.\.venv\Scripts\python.exe scripts/deploy_aws.py
```

This writes `output/aws/user-data.sh` and `output/aws/deployment-plan.json` without contacting AWS or creating resources. Review these files before launching.

The AWS session was expired during initial preparation. Refresh it privately:

```powershell
aws login
.\.venv\Scripts\python.exe scripts/deploy_aws.py --plan
```

The plan checks the current AWS account, Ubuntu blueprint, availability zone and current bundle price using read-only calls. Account and region must match the intended deployment. It does not create resources.

## Launch after cost approval

```powershell
.\.venv\Scripts\python.exe scripts/deploy_aws.py --apply
```

This creates a billed instance. Do not run it until launch and the price cap have been approved. Existing instances with the same name are never overwritten. The bootstrap installs Docker, downloads the pinned source, builds the image, starts it, waits for container health and executes real saved-model inference. Allow roughly 5–15 minutes; actual time depends on package downloads and server performance.

Check deployment:

```powershell
.\.venv\Scripts\python.exe scripts/deploy_aws.py --check
```

Use the actual URL returned by AWS. A successful health check is only one check; open the dashboard and submit a prediction before calling deployment verified. The current HTTP demo does not provide TLS; a production deployment needs a domain and HTTPS. Public IP may change after a stop/start.

## Server diagnostics

Open the instance's browser SSH terminal in the Lightsail console:

```sh
sudo tail -n 100 /var/log/batterytwin-deploy.log
sudo docker logs --tail 100 batterytwin
sudo docker inspect --format '{{.State.Health.Status}}' batterytwin
sudo cat /opt/batterytwin-inference.json
sudo docker exec batterytwin python scripts/smoke_inference.py
```

## Stop charges

Stopping a Lightsail instance does not stop its instance billing. Delete the specific demo instance when you no longer need it, after preserving any needed changes. The following deletes that server and its local disk; it is a manual cleanup step, not part of deployment:

```powershell
aws lightsail delete-instance --region us-east-1 --instance-name batterytwin-streamlit
```

Current status is recorded in `artifacts/results/aws_deployment.json`. Prepared files are not evidence of a successful Docker build or live AWS deployment.
