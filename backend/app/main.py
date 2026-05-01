import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.router import api_router
from app.utils.logger import configure_logging

configure_logging()


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """Trust X-Forwarded-Proto so redirects and URL generation use HTTPS behind Railway/proxies."""

    async def dispatch(self, request: Request, call_next):
        if request.headers.get('x-forwarded-proto') == 'https':
            request.scope['scheme'] = 'https'
        return await call_next(request)


app = FastAPI()

app.add_middleware(ProxyHeadersMiddleware)

_cors_origins = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:4173',
    'http://127.0.0.1:4173',
]
for origin in os.getenv('CORS_ORIGINS', '').split(','):
    if origin := origin.strip().rstrip('/'):
        _cors_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(api_router)


@app.get('/')
def root() -> str:
    return 'Hello world!'
