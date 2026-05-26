import os
import json
import tempfile
from contextlib import asynccontextmanager

from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from starlette.applications import Starlette
from starlette.routing import Mount

from utils.logger import get_logger

logger = get_logger()

# ── Environment ───────────────────────────────────────────────────────────────

load_dotenv(find_dotenv())
FASTAPI_ENV = os.getenv("APP_ENV", "development").lower()
logger.info(f"APP_ENV: {FASTAPI_ENV}")

# ── Google service account ────────────────────────────────────────────────────
# Reads the service account JSON from an env var and writes it to a temp file.
# Sets GOOGLE_APPLICATION_CREDENTIALS so all GCP SDKs (Vertex AI, ADK, etc.)
# pick it up automatically without any code changes.

_sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
if _sa_json:
    try:
        _sa_dict = json.loads(_sa_json)
        _sa_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,       # must persist for the process lifetime
        )
        json.dump(_sa_dict, _sa_file)
        _sa_file.flush()
        _sa_file.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _sa_file.name
        logger.info(
            f"Service account loaded from GOOGLE_SERVICE_ACCOUNT_JSON. "
            f"GOOGLE_APPLICATION_CREDENTIALS={_sa_file.name}"
        )
    except (json.JSONDecodeError, OSError) as e:
        logger.error(
            f"Failed to load GOOGLE_SERVICE_ACCOUNT_JSON: {e}. "
            "GCP calls will use default credentials."
        )
elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    logger.info(
        f"Using GOOGLE_APPLICATION_CREDENTIALS="
        f"{os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}"
    )
else:
    logger.warning(
        "No GCP credentials configured. "
        "Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS."
    )

# ── Settings ──────────────────────────────────────────────────────────────────

from src.config.development import DevSettings
from src.config.staging import StagingSettings
from src.config.production import ProductionSettings

_settings_map = {
    "development": DevSettings,
    "staging": StagingSettings,
    "production": ProductionSettings,
}

if FASTAPI_ENV not in _settings_map:
    raise ValueError(
        f"Unknown APP_ENV: '{FASTAPI_ENV}'. "
        f"Valid values: {list(_settings_map.keys())}"
    )

settings = _settings_map[FASTAPI_ENV]()
logger.info(f"Settings loaded: {type(settings).__name__}")

# ── Container ─────────────────────────────────────────────────────────────────

import src.api.intake.router
import src.api.triage.router
import src.api.consult.router
import src.api.evaluation.router

from src.config.dependency_injection.container import Container

container = Container()
container.wire(
    modules=[
        src.api.intake.router,
        src.api.triage.router,
        src.api.consult.router,
        src.api.evaluation.router,
    ]
)

# ── Routers ───────────────────────────────────────────────────────────────────

from src.api.intake.router import router as intake_router
from src.api.triage.router import router as triage_router
from src.api.consult.router import router as consult_router
from src.api.evaluation.router import router as evaluation_router

# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown lifecycle.

    Startup order:
    1. Init DI container resources
    2. Connect Redis
    3. Instrument Phoenix observability (registers OTEL tracer)
    4. Validate Phoenix MCP tools are available
    5. Run DB connectivity check

    Shutdown order (reverse):
    1. Disconnect Redis
    2. Shutdown Phoenix tracer provider
    3. Shutdown container resources
    """
    logger.info("── Clinical Copilot starting up ──")

    # 1 — DI container
    container.init_resources()
    logger.info("DI container initialised")

    # 2 — Redis
    try:
        await container.redis_client().connect()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(
            f"Redis connection failed: {e}. "
            "Cache will be unavailable — app continues."
        )

    # 3 — Phoenix observability
    # Must run before any ADK agent call so traces are captured from the start
    try:
        observability = container.observability()
        observability.instrument()
        logger.info("Phoenix observability instrumented")
    except Exception as e:
        logger.warning(
            f"Phoenix instrumentation failed: {e}. "
            "Tracing will be unavailable — app continues."
        )

    # 4 — Validate Phoenix MCP tools
    # Non-fatal — logs missing tools but does not block startup
    if settings.PHOENIX_MODE != "noop":
        try:
            from src.core.mcp.protocols import PhoenixTools
            mcp = container.mcp_client()
            expected_tools = [
                PhoenixTools.GET_SPANS,
                PhoenixTools.GET_SPAN_ANNOTATIONS,
                PhoenixTools.UPSERT_PROMPT,
                PhoenixTools.GET_PROMPT_VERSION_BY_TAG,
                PhoenixTools.ADD_PROMPT_VERSION_TAG,
            ]
            await mcp.validate_expected_tools(expected_tools)
        except Exception as e:
            logger.warning(
                f"Phoenix MCP tool validation failed: {e}. "
                "Evaluation pipeline may not work correctly."
            )

    # 5 — DB connectivity check
    try:
        db = container.db_engine()
        async with db.session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        logger.info("Database connectivity confirmed")
    except Exception as e:
        # Fatal — app cannot function without DB
        logger.error(f"Database connectivity check failed: {e}")
        raise

    logger.info("── Clinical Copilot ready ──")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────

    logger.info("── Clinical Copilot shutting down ──")

    try:
        await container.redis_client().disconnect()
        logger.info("Redis disconnected")
    except Exception as e:
        logger.warning(f"Redis disconnect error: {e}")

    try:
        observability = container.observability()
        observability.shutdown()
    except Exception:
        pass

    container.shutdown_resources()
    logger.info("── Clinical Copilot shutdown complete ──")

# ── FastAPI app ───────────────────────────────────────────────────────────────

api_app = FastAPI(
    title="Clinical Copilot",
    version=getattr(settings, "VERSION", "0.1.0"),
    description=(
        "AI-powered clinical decision support and triage agent "
        "for resource-constrained healthcare systems."
    ),
    lifespan=lifespan,
    root_path=os.getenv("API_ROOT_PATH", ""),
    docs_url="/api/v1/docs" if FASTAPI_ENV != "production" else None,
    redoc_url="/api/redoc" if FASTAPI_ENV != "production" else None,
)

# Attach container to app state
api_app.container = container

# ── CORS ──────────────────────────────────────────────────────────────────────

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "CORS_ORIGINS", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# ── Routers ───────────────────────────────────────────────────────────────────

api_app.include_router(
    intake_router,
    prefix=f"{settings.API_V_STR}",
    tags=["Intake"],
)
api_app.include_router(
    triage_router,
    prefix=f"{settings.API_V_STR}",
    tags=["Triage"],
)
api_app.include_router(
    consult_router,
    prefix=f"{settings.API_V_STR}",
    tags=["Consult"],
)
api_app.include_router(
    evaluation_router,
    prefix=f"{settings.API_V_STR}",
    tags=["Evaluation"],
)

# ── Health endpoints ──────────────────────────────────────────────────────────

@api_app.get("/", status_code=200, tags=["Health"])
def root() -> dict:
    return {
        "service": "Clinical Copilot",
        "version": getattr(settings, "VERSION", "0.1.0"),
        "environment": FASTAPI_ENV,
        "status": "healthy",
    }


@api_app.get("/health", status_code=200, tags=["Health"])
async def health_check() -> dict:
    """
    Liveness probe.
    Checks Redis and DB connectivity.
    """
    checks: dict[str, str] = {}

    # Redis
    try:
        redis_ok = await container.redis_client().ping()
        logger.info(f"\n redis status: {redis_ok} \n")
        checks["redis"] = "ok" if redis_ok else "degraded"
    except Exception as e:
        checks["redis"] = f"unavailable: {e}"

    # DB
    try:
        db = container.db_engine()
        async with db.session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"unavailable: {e}"

    # Phoenix MCP
    try:
        mcp_ok = await container.mcp_client().health_check()
        checks["phoenix_mcp"] = "ok" if mcp_ok else "degraded"
    except Exception as e:
        checks["phoenix_mcp"] = f"unavailable: {e}"

    # LLM
    try:
        llm_ok = await container.llm_client().health_check()
        checks["llm"] = "ok" if llm_ok else "degraded"
    except Exception as e:
        checks["llm"] = f"unavailable: {e}"

    overall = (
        "healthy"
        if all(v == "ok" for v in checks.values())
        else "degraded"
    )

    return {
        "status": overall,
        "version": getattr(settings, "VERSION", "0.1.0"),
        "environment": FASTAPI_ENV,
        "checks": checks,
    }


@api_app.get("/health/agents", status_code=200, tags=["Health"])
async def agent_health_check() -> dict:
    """
    Agent readiness probe.
    Confirms each agent runtime can be instantiated.
    Separate from /health so liveness and readiness can be probed independently.
    """
    checks: dict[str, str] = {}

    factory = container.agent_factory()

    for agent_name, build_fn in [
        ("triage_agent", factory.build_triage_agent),
        ("documentation_agent", factory.build_documentation_agent),
        ("evaluator_agent", factory.build_evaluator_agent),
    ]:
        try:
            agent = build_fn()
            ok = await agent.health_check()
            checks[agent_name] = "ok" if ok else "degraded"
        except Exception as e:
            checks[agent_name] = f"unavailable: {e}"

    overall = (
        "ready"
        if all(v == "ok" for v in checks.values())
        else "degraded"
    )

    return {"status": overall, "agents": checks}


# ── Exception handlers ────────────────────────────────────────────────────────

@api_app.exception_handler(RequestValidationError)
async def request_validation_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = [
        f"{'.'.join(str(l) for l in err['loc'])}: {err['msg']}"
        for err in exc.errors()
    ]
    logger.warning(f"Validation error on {request.url.path}: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": {
                "status": "failed",
                "message": "Validation error",
                "errors": errors,
            }
        },
    )


@api_app.exception_handler(ValidationError)
async def pydantic_validation_handler(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    logger.warning(f"Pydantic error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": {
                "status": "failed",
                "message": "Invalid data format",
                "errors": exc.errors(),
            }
        },
    )


@api_app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    message = str(exc) if FASTAPI_ENV != "production" else "An internal error occurred"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": {"status": "error", "message": message}},
    )


# ── Mount ─────────────────────────────────────────────────────────────────────

# mount_path = os.getenv("MOUNT_PATH", "")

# if mount_path:
#     logger.info(f"Mounting at: {mount_path}")
#     root_app = Starlette(routes=[Mount(mount_path, app=api_app)])
# else:
#     root_app = Starlette(routes=[Mount("/", app=api_app)])

# root_app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["127.0.0.1"])

# app = root_app

# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    # print(f"Port: {settings.PORT} \n")

    is_dev = FASTAPI_ENV == "development"
    uvicorn.run(
        # "main:app",
        "main:api_app",
        host="0.0.0.0",
        port=int(settings.PORT or 8000),
        reload=is_dev,
        log_level=getattr(settings, "LOG_LEVEL", "info").lower(),
        workers=None if is_dev else 2,
    )