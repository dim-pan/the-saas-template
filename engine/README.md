# Engine

The Engine is a Python package built with a `src/` layout for clean imports and
distribution.

## Development

Create a virtual environment, install dependencies, and run checks:

1. Install uv with `make install-uv`
2. Install dev dependencies with `make install-dev`
3. Run checks with `make lint-check`
4. Run tests with `make test`
5. Copy `.env.example` to `.env` and fill in values
6. Run gateway with `make dev-gateway`
7. Run worker with `make dev-worker`

### Optional: Infisical-managed secrets

To pull secrets from Infisical instead of `.env`:

1. Install [infisical](https://infisical.com/docs/cli/overview) and run `infisical login`
2. Set `INFISICAL_PROJECT_ID` (in shell or `engine/.env`)
3. Run `make dev-gateway USE_INFISICAL=1` / `make dev-worker USE_INFISICAL=1`

## AWS IAM

1. Install AWS CLI
2. Create a new IAM user with the SQS permissions.
3. Create a new access key for the user. Save the access key ID and secret access key.
4. Run `aws configure` and enter the access key ID and secret access key. Region should be `us-east-2`. Output format should be `json`.
5. Run `aws sts get-caller-identity --region us-east-2` to verify the credentials.
6. If it didn't error you're good to go.