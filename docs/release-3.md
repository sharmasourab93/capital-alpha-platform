# Release 3

## TODO - Next Release Hardening

Before the next release, harden the data-layer deployment path created in PR #3.

- Add IAM authorization for `/account/*` routes and require SigV4-signed client requests.
- Move AngelOne broker credentials to AWS Secrets Manager; pass only the secret ARN/config reference into Lambda.
- Replace static AWS deploy keys with GitHub OIDC role assumption.
- Make Lambda artifact deployment deterministic using locked dependencies and commit-SHA-based artifact keys.
- Add tests for Lambda/API Gateway stage-prefix path normalization.
- Document why `int` and `prod` egress configs are intentionally blank until those environments are active.
- Update deployment runbook with stack order, smoke tests, and rollback steps.

S3 bucket naming remains unchanged by business decision.
