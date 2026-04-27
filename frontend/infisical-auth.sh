#!/bin/sh
if [ -z "$INFISICAL_CLIENT_ID" ] || [ -z "$INFISICAL_CLIENT_SECRET" ] || [ -z "$INFISICAL_PROJECT_ID" ]; then
    echo "Infisical credentials not set; starting without Infisical."
    exec pnpm exec vite --host 0.0.0.0 --port 5173
fi

export INFISICAL_TOKEN=$(infisical login --method=universal-auth --client-id=$INFISICAL_CLIENT_ID --client-secret=$INFISICAL_CLIENT_SECRET --plain --silent)
exec infisical run --token $INFISICAL_TOKEN --projectId $INFISICAL_PROJECT_ID --env $INFISICAL_SECRET_ENV --domain $INFISICAL_DOMAIN -- pnpm exec vite --host 0.0.0.0 --port 5173
