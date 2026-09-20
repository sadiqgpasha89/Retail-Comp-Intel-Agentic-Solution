"""FastAPI Application Entrypoint: lifespan management, catalog pre-loading, and route mounting."""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from retail_intel.core.config import settings
from retail_intel.core.logging import configure_logging, get_logger
from retail_intel.api.middleware import CorrelationIDMiddleware
from retail_intel.api.schemas import HealthResponse
from retail_intel.data_engineering.ingestion.ingestion_pipeline import IngestionPipeline
from retail_intel.data_engineering.normalization.normalization_pipeline import (
    NormalizationPipeline, NormalizedProductRecord,
)
from retail_intel.data_engineering.feature_store.feature_store import FeatureStore
from retail_intel.data_engineering.stream.stream_broker import StreamBroker
from retail_intel.datascience.tier1_rules.deterministic_engine import DeterministicRuleEngine
from retail_intel.datascience.tier2_ml.bi_encoder import BiEncoderCandidateRetriever
from retail_intel.datascience.tier2_ml.cross_encoder import CrossEncoderScorer
from retail_intel.datascience.tier2_ml.anomaly_detector import PricingAnomalyDetector
from retail_intel.agents.tools.tool_registry import ToolRegistry
from retail_intel.agents.supervisor import SupervisorAgent
from retail_intel.hitl.review_queue import HITLReviewQueue
from retail_intel.metrics.engine import MetricsEngine
from retail_intel.mlops.drift_radar import DriftRadar

from retail_intel.api.routes.intelligence import router as intelligence_router
from retail_intel.api.routes.catalog import router as catalog_router
from retail_intel.api.routes.metrics import router as metrics_router
from retail_intel.api.routes.drift import router as drift_router
from retail_intel.api.routes.hitl import router as hitl_router
from retail_intel.api.routes.graph import router as graph_router
from retail_intel.api.routes.pipelines import router as pipelines_router
from retail_intel.api.routes.recommendations import router as recommendations_router
from retail_intel.api.routes.chaos import router as chaos_router

configure_logging(settings.log_level)
logger = get_logger("api.main")


class ApplicationState:
    """
    Per-application service context.
    Stored on app.state.app_state (not a module-level global) so that
    each FastAPI worker process owns its own independent instance.
    """
    def __init__(self):
        self.internal_raw_list: List[Dict[str, Any]] = []
        self.competitor_raw_list: List[Dict[str, Any]] = []
        self.competitor_raw_dict: Dict[str, Dict[str, Any]] = {}
        self.internal_dict: Dict[str, NormalizedProductRecord] = {}
        self.internal_records: List[NormalizedProductRecord] = []

        # Service instances — initialised in lifespan to respect async context
        self.normalizer = NormalizationPipeline()
        self.ingestion_pipeline = IngestionPipeline()
        self.feature_store = FeatureStore()
        self.stream_broker = StreamBroker()
        self.rule_engine = DeterministicRuleEngine()
        self.bi_encoder = BiEncoderCandidateRetriever(self.feature_store)
        self.cross_encoder = CrossEncoderScorer()
        self.anomaly_detector = PricingAnomalyDetector()
        self.tools = ToolRegistry()
        self.supervisor = SupervisorAgent(self.tools)
        self.hitl_queue = HITLReviewQueue()
        self.metrics_engine = MetricsEngine()
        self.drift_radar = DriftRadar()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialises catalogs and vector indexes on startup; gracefully shuts down on exit."""
    state = ApplicationState()
    app.state.app_state = state  # Store on app.state for DI access

    logger.info("Initialising Retail Competitor Intelligence Platform", mode=settings.execution_mode.value)

    # Load catalogs asynchronously via executor to avoid blocking the event loop
    loop = asyncio.get_event_loop()

    def _load_json(path: Path) -> list:
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 1. Internal catalog
    internal_raw = await loop.run_in_executor(None, _load_json, settings.internal_catalog_path)
    if internal_raw:
        state.internal_raw_list = internal_raw
        state.internal_records = [
            state.normalizer.normalize_internal_product(item) for item in internal_raw
        ]
        state.internal_dict = {r.sku: r for r in state.internal_records}
        state.rule_engine.build_gtin_index(state.internal_records)
        state.feature_store.index_internal_catalog(state.internal_records)
        logger.info("Internal catalog loaded", count=len(state.internal_records))

    # 2. Competitor catalog
    competitor_raw = await loop.run_in_executor(None, _load_json, settings.competitor_catalog_path)
    if competitor_raw:
        state.competitor_raw_list = competitor_raw
        state.competitor_raw_dict = {item["competitor_sku"]: item for item in competitor_raw}
        logger.info("Competitor catalog loaded", count=len(state.competitor_raw_list))

    yield

    logger.info("Shutting down Retail Competitor Intelligence Platform.")


def create_app() -> FastAPI:
    """Application factory — enables clean testing and multi-worker deployments."""
    _app = FastAPI(
        title="Retail Competitor Intelligence — Autonomous Hybrid Platform",
        version="1.1.0",
        lifespan=lifespan,
    )

    # 1. Correlation ID middleware (add first so it wraps all handlers)
    _app.add_middleware(CorrelationIDMiddleware)

    # 2. CORS — explicit origin list (wildcard + credentials is spec-invalid)
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 3. API Routers
    _app.include_router(intelligence_router)
    _app.include_router(catalog_router)
    _app.include_router(metrics_router)
    _app.include_router(drift_router)
    _app.include_router(hitl_router)
    _app.include_router(graph_router)
    _app.include_router(pipelines_router)
    _app.include_router(recommendations_router)
    _app.include_router(chaos_router)

    # 4. Static files & Jinja2 templates
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    if not frontend_dir.exists():
        frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

    static_dir = frontend_dir / "static"
    templates_dir = frontend_dir / "templates"

    if static_dir.exists():
        _app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    jinja_env = (
        Environment(loader=FileSystemLoader(str(templates_dir)))
        if templates_dir.exists()
        else None
    )

    @_app.get("/health", response_model=HealthResponse)
    async def health_check(request: Request):
        """System liveness and readiness probe."""
        state: ApplicationState = request.app.state.app_state
        return HealthResponse(
            status="HEALTHY",
            app_name=settings.app_name,
            execution_mode=settings.execution_mode.value,
            internal_catalog_size=len(state.internal_records),
            competitor_catalog_size=len(state.competitor_raw_list),
            vector_dimension=settings.vector_dimension,
        )

    @_app.get("/", response_class=HTMLResponse)
    @_app.get("/dashboard", response_class=HTMLResponse)
    async def serve_dashboard(request: Request):
        """Serves the glassmorphic single-page frontend application."""
        if jinja_env:
            template = jinja_env.get_template("index.html")
            return HTMLResponse(template.render(
                app_name="AuraIntel | Enterprise Retail Competitor Intelligence",
                execution_mode=settings.execution_mode.value,
            ))
        return HTMLResponse("<h1>Retail Competitor Intelligence Dashboard (Template loading...)</h1>")

    return _app


# Application instance — used by uvicorn and pytest TestClient
app = create_app()
