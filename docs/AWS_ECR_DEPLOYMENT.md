# ECR, CodeBuild and ECS deployment

ECR stores the private Docker image. CodeBuild builds and tests the image remotely. ECS Fargate runs the Streamlit application. This is the current requested AWS approach; the earlier Lightsail launcher is an alternative and has not been launched.

## Prepared resources

`output/aws-ecr/build.json` creates the private `batterytwin` ECR repository, a CodeBuild project, a scoped build role and seven-day build logs. CodeBuild downloads the approved public source at commit `ab5ba052e5779c10652fb32747324213a5895f23`, builds the existing Dockerfile, runs saved-model inference and a Streamlit HTTP health check, then pushes the image. It uses a 30-minute build timeout. Local Docker Desktop is optional. No credentials or personal lab records are sent to the builder.

`output/aws-ecr/app.json` creates a dedicated VPC, public subnet and internet gateway, security group, ECS cluster, scoped image-pull execution role, logs and one Fargate task with 0.5 vCPU and 4 GB RAM. Only TCP 7860 is exposed. The runtime image is pinned by SHA-256 digest. No NAT gateway or load balancer is provisioned. The task's public HTTP address changes when its network interface is replaced; this is a class-demo setup. A stable HTTPS deployment needs additional domain/load-balancer configuration and costs.

## Cost review

For 730 hours in us-east-1, the published Linux/x86 Fargate rates imply approximately $27.75 for 0.5 vCPU and 4 GB RAM, plus $3.65 for one public IPv4 address: approximately **$31.40/month before other charges**. ECR storage is billed by GB-month; build minutes, CloudWatch logs, outbound transfer and taxes add to this. These are estimates, not a spending cap, and account credits are not assumed. Replacements may briefly overlap in billing. The desired count is one and the maximum deployment percentage is 100.

Sources: [Fargate rates](https://aws.amazon.com/fargate/pricing/), [public IPv4 pricing](https://aws.amazon.com/vpc/pricing/), [ECR storage pricing](https://aws.amazon.com/ecr/pricing/), [CodeBuild pricing](https://aws.amazon.com/codebuild/pricing/).

## Prepare and validate

```powershell
.\.venv\Scripts\python.exe scripts/deploy_ecr.py
aws login --profile default
aws sts get-caller-identity --profile default
.\.venv\Scripts\python.exe scripts/deploy_ecr.py --plan
```

Default mode only writes local templates. `--plan` checks identity and asks AWS to validate both templates; it creates nothing. Review the account, region, IAM policies and costs before proceeding. AWS login is now active and both templates passed AWS server-side validation.

## Deploy after cost approval

Run these stages sequentially; wait for the preceding stage to succeed before continuing:

```powershell
.\.venv\Scripts\python.exe scripts/deploy_ecr.py --create-build
aws cloudformation describe-stacks --stack-name batterytwin-build --region us-east-1 --query 'Stacks[0].StackStatus'
# Wait for CREATE_COMPLETE before requesting the build:
.\.venv\Scripts\python.exe scripts/deploy_ecr.py --start-build
.\.venv\Scripts\python.exe scripts/deploy_ecr.py --build-status
# Continue only after SUCCEEDED:
.\.venv\Scripts\python.exe scripts/deploy_ecr.py --deploy-app
aws cloudformation describe-stacks --stack-name batterytwin-app --region us-east-1 --query 'Stacks[0].StackStatus'
# Wait for CREATE_COMPLETE:
.\.venv\Scripts\python.exe scripts/deploy_ecr.py --check
```

Creation stages create billed resources. CodeBuild receives permissions to push only to this repository and write only its build logs; the ECS execution role can pull that repository and write app logs. No application task role is granted. Stack creation declares CAPABILITY_IAM for these roles. Existing stacks are not overwritten. ECR tags are immutable: if the same revision already exists, inspect it and reuse it rather than blindly repeating the build.

The deployment helper records build IDs, image digest and task status in `artifacts/results/aws_ecr_deployment.json`. Use the real public URL returned by `--check` to inspect `/_stcore/health`, open the UI, and test predictions. A prepared template, successful push or running task alone does not prove a working application. If CloudFormation fails, read stack events; if a build fails, read its returned CloudWatch logs. Do not retry resource creation without checking the existing state.

## Cleanup

To stop ongoing task charges, scale the specific service to zero or delete the `batterytwin-app` stack after preserving needed evidence. Delete `batterytwin-build` when no longer needed. The private ECR repository is retained deliberately, so images remain stored and incur storage charges until explicitly removed. Deleting it is a separate destructive action; confirm that its images are no longer needed first. The helper performs no automatic cleanup or deletion.

Current status: **deployed and verified** on October 15, 2026. [Open BatteryTwin](http://3.238.69.149:7860). Both CloudFormation stacks completed. CodeBuild succeeded, the Docker image was pushed to ECR, and ECS reports one RUNNING/HEALTHY task. Public health returned HTTP 200 with `ok`. Browser checks verified the dashboard and a capacity edit to 1.60 Ah, producing 80.3% next-cycle SOH and approximately 52 remaining cycles. Eight deployment guard tests passed. Evidence: `artifacts/results/aws_ecr_deployment.json` and `artifacts/screenshots/aws-dashboard.png` / `aws-prediction.png`.

Image digest: `sha256:2b75fdbec47a0ed179f6982c629e7eeee3b0d7a85642d81bd1e1a5e596fe3530`. Build ID: `batterytwin:c35c975d-4116-420e-9e34-3111e66a75bc`. The image and service are running in us-east-1. Approved charges continue while the task runs; ECR storage remains billable after stopping the task. The public IP is tied to this task and can change upon replacement.
