from fastapi import APIRouter

from .assets import router as assets_router
from .jobs import org_level_router as org_level_jobs_router
from .jobs import router as jobs_router
from .memberships import router as memberships_router
from .organizations import router as organizations_router
from .stripe import router as stripe_router
from .users import router as users_router

v1_router = APIRouter(prefix='/v1')
v1_router.include_router(users_router)
v1_router.include_router(organizations_router)
v1_router.include_router(memberships_router)
v1_router.include_router(stripe_router)
v1_router.include_router(assets_router)
v1_router.include_router(jobs_router)
v1_router.include_router(org_level_jobs_router)
