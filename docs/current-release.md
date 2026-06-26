# Current Release Notes

## Data Layer AWS Foundation

This release establishes the first deployable AWS path for the Capital Alpha data layer.

### Included

- VPC CloudFormation stack with public/private subnets, NAT egress, route tables, workload security group, and S3/Secrets Manager/STS VPC endpoints.
- S3 artifact bucket stack for Lambda zip and rendered OpenAPI deployment artifacts.
- Generic Lambda CloudFormation stack for zip-based Python 3.13 Lambda deployment.
- API Gateway HTTP API CloudFormation stack using OpenAPI 3.0 routes from `data_layer/data-layer-rest.openapi.yaml`.
- GitHub Actions workflows for network, S3, Lambda, API Gateway deployment, and guarded CloudFormation stack deletion.
- Branch-to-environment deployment rules:
  - `main` deploys `prod`
  - `qa` deploys `int`
  - all other branches deploy `dev`
- Lambda runtime fixes for:
  - lazy broker adapter imports
  - SmartAPI log writes under Lambda's writable `/tmp`
  - API Gateway stage-prefix path normalization

### Current Notes

- API Gateway is currently an HTTP API, not a REST API. Native API keys and usage plans are not supported in this mode.
- OpenAPI is kept as source under `data_layer/`; deployment renders the Lambda invoke URI before uploading to S3.
- AngelOne credentials are currently injected as Lambda environment variables through deployment parameters. Secrets Manager remains the preferred production hardening path.
- Public broker access from Lambda depends on VPC NAT egress and workload security-group egress rules.
