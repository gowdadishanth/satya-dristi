import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.errors import SatyaDristiError
from app.api.v1.auth import router as auth_router
from app.api.v1.earth import router as earth_router
from app.api.v1.analyses import router as analyses_router
from app.api.v1.history import router as history_router
from app.api.v1.reports import router as reports_router
from app.api.v1.system import router as system_router

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("satya_dristi")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTOR,
    version=settings.VERSION,
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "Content-Type"],
)

# Static file access for evidence and reports
app.mount("/static/evidence", StaticFiles(directory=str(settings.EVIDENCE_DIR)), name="evidence")
app.mount("/static/reports", StaticFiles(directory=str(settings.REPORTS_DIR)), name="reports")

# Exception handler for domain errors
@app.exception_handler(SatyaDristiError)
async def satya_dristi_error_handler(request: Request, exc: SatyaDristiError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )

# Include API v1 routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(earth_router, prefix=settings.API_V1_PREFIX)
app.include_router(analyses_router, prefix=settings.API_V1_PREFIX)
app.include_router(history_router, prefix=settings.API_V1_PREFIX)
app.include_router(reports_router, prefix=settings.API_V1_PREFIX)
app.include_router(system_router, prefix=settings.API_V1_PREFIX)

@app.get("/")
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "descriptor": settings.PROJECT_DESCRIPTOR,
        "version": settings.VERSION,
        "status": "operational",
        "docs": f"{settings.API_V1_PREFIX}/docs"
    }
