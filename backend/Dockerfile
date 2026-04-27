FROM python:3.12-slim

ARG USE_INFISICAL=0

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install OS deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates bash \
    && rm -rf /var/lib/apt/lists/*

# Install Infisical CLI (only when USE_INFISICAL=1)
RUN if [ "$USE_INFISICAL" = "1" ]; then \
        curl -1sLf 'https://artifacts-cli.infisical.com/setup.deb.sh' | bash \
        && apt-get update \
        && apt-get install -y --no-install-recommends infisical \
        && rm -rf /var/lib/apt/lists/*; \
    fi

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy only dependency manifests first
COPY pyproject.toml uv.lock ./
RUN uv sync --locked

# Copy the rest of the application code
COPY app ./app
COPY infisical-auth.sh ./infisical-auth.sh
RUN chmod +x ./infisical-auth.sh

EXPOSE 8000

CMD ["./infisical-auth.sh"]
