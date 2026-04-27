FROM node:22-bookworm-slim

ARG USE_INFISICAL=0

WORKDIR /app

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

# pnpm via corepack
RUN corepack enable

# deps first (cache-friendly)
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# app code
COPY . .
COPY infisical-auth.sh ./infisical-auth.sh
RUN chmod +x ./infisical-auth.sh

EXPOSE 5173

CMD ["./infisical-auth.sh"]
