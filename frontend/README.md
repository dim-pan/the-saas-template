# The Frontend

## Setup

1. Install dependencies

```bash
pnpm install
```

2. Suggested VSCode Extensions:

- BiomeJS
- ESLint
- Prettier
- Playwright
- Vitest

3. Verify BiomeJS is working with

```bash
pnpm format
pnpm lint
```

4. Copy `.env.example` to `.env` and fill in values, then run:

```bash
pnpm dev
```

## Optional: Infisical-managed secrets

To pull secrets from Infisical instead of `.env`:

1. [Install Infisical CLI](https://infisical.com/docs/cli/overview)
2. `infisical login`
3. `infisical init`
4. Run `pnpm dev:infisical`
