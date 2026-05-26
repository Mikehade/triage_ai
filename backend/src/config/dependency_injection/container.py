from __future__ import annotations
from dependency_injector import containers, providers

from src.config.base import get_settings

# Database
from src.infrastructure.db.session import Database

# Cache
from src.infrastructure.cache.redis_client import RedisClient
from src.infrastructure.cache.redis_manager import RedisCacheManager
from src.infrastructure.cache.redis_service import CacheService

# LLM
from src.infrastructure.language_models.gemini import GeminiClient
# from src.infrastructure.language_models.openai import OpenAIClient

# MCP
from src.infrastructure.mcp.phoenix_mcp import PhoenixMCPClient
from src.infrastructure.mcp.noop_mcp import NoopMCPClient
from src.infrastructure.mcp.prompt_registry import PhoenixPromptRegistry

# Observability
from src.infrastructure.observability.phoenix import PhoenixObservability
from src.infrastructure.observability.noop import NoopObservability

# Knowledge
from src.infrastructure.knowledge.vertex_datastore import VertexKnowledgeStore

# Repositories
from src.infrastructure.repository.patient_repository import (
    PatientRepository,
    IntakeRepository,
)
from src.infrastructure.repository.triage_repository import (
    TriageResultRepository,
    PatientBriefRepository,
)
from src.infrastructure.repository.documentation_repository import (
    ClinicalNoteRepository,
    ReferralLetterRepository,
    DischargeSummaryRepository,
)
from src.infrastructure.repository.evaluation_repository import (
    EvalScoreRepository,
    PromptImprovementRepository,
)

# Tools — triage
from src.infrastructure.tools.triage.urgency_score import UrgencyScoreTool
from src.infrastructure.tools.triage.differential_diagnosis import DifferentialDiagnosisTool
from src.infrastructure.tools.triage.drug_interaction_check import DrugInteractionTool
from src.infrastructure.tools.triage.assemble_brief import AssembleBriefTool

# Tools — documentation
from src.infrastructure.tools.documentation.draft_clinical_note import DraftClinicalNoteTool
from src.infrastructure.tools.documentation.draft_referral import DraftReferralTool
from src.infrastructure.tools.documentation.draft_discharge import DraftDischargeTool

# Tools — evaluation
from src.infrastructure.tools.evaluation.get_traces import GetTracesTool
from src.infrastructure.tools.evaluation.get_annotations import GetAnnotationsTool
from src.infrastructure.tools.evaluation.upsert_prompt import UpsertPromptTool

# Agent factory
from src.infrastructure.agents.adk.factory import ADKAgentFactory

# Services
from src.infrastructure.services.patient_service import PatientService
from src.infrastructure.services.triage_service import TriageService
from src.infrastructure.services.documentation_service import DocumentationService
from src.infrastructure.services.evaluation_service import EvaluationService

# Use cases
from src.application.triage_patient import TriagePatientUseCase
from src.application.generate_note import GenerateNoteUseCase
from src.application.generate_referral import GenerateReferralUseCase
from src.application.generate_discharge import GenerateDischargeUseCase
from src.application.evaluate_agent import EvaluateAgentUseCase


def _make_mcp_client(settings) -> PhoenixMCPClient | NoopMCPClient:
    """
    Return NoopMCPClient when PHOENIX_MODE=noop.
    Allows full local development without npx or Phoenix Cloud.
    """
    if settings.PHOENIX_MODE == "noop":
        return NoopMCPClient()
    return PhoenixMCPClient(
        api_key=settings.PHOENIX_API_KEY,
        # collector_endpoint=settings.PHOENIX_COLLECTOR_ENDPOINT,
        collector_endpoint=settings.phoenix_endpoint,   # ← property
        project_name=settings.PHOENIX_PROJECT_NAME,
    )


def _make_llm_client(settings) -> GeminiClient: #| OpenAIClient:
    """
    Return the configured LLM provider.
    Swap LLM_PROVIDER=openai to switch — zero code changes.
    """
    # if settings.LLM_PROVIDER == "openai":
    #     return OpenAIClient(
    #         api_key=settings.OPENAI_API_KEY,
    #         model=settings.OPENAI_MODEL,
    #     )
    return GeminiClient(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
    )


def _make_observability(settings) -> PhoenixObservability | NoopObservability:
    if settings.PHOENIX_MODE == "noop":
        return NoopObservability()
    return PhoenixObservability(
        project_name=settings.PHOENIX_PROJECT_NAME,
        # endpoint=settings.PHOENIX_COLLECTOR_ENDPOINT,
        collector_endpoint=settings.phoenix_endpoint,   # ← property
        api_key=settings.PHOENIX_API_KEY if settings.PHOENIX_MODE == "cloud" else None,
    )


class Container(containers.DeclarativeContainer):

    wiring_config = containers.WiringConfiguration(
        packages=["src.api"],
    )

    # ── Config ────────────────────────────────────────────────────────────────

    config = providers.Singleton(get_settings)

    # ── Database ──────────────────────────────────────────────────────────────

    db_engine = providers.Singleton(
        Database,
        providers.Callable(
            lambda cfg: cfg.SQLALCHEMY_DATABASE_URI.replace(
                "postgresql://", "postgresql+asyncpg://"
            ),
            config,
        ),
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=300,
        pool_pre_ping=True,
        connect_args={
            "statement_cache_size": 0,
            "timeout": 60,
            "command_timeout": 60,
            "server_settings": {
                "application_name": "clinical-copilot",
                "jit": "off",
            },
        },
        pool_reset_on_return="rollback",
    )

    # ── Cache ─────────────────────────────────────────────────────────────────

    redis_client = providers.Singleton(
        RedisClient,
        url=providers.Callable(lambda cfg: cfg.REDIS_URL, config),
        redis_host=providers.Callable(lambda cfg: cfg.REDIS_HOST, config),
        redis_port=providers.Callable(lambda cfg: cfg.REDIS_PORT, config),
        redis_password=providers.Callable(lambda cfg: cfg.REDIS_PASSWORD, config),
        redis_db=providers.Callable(lambda cfg: cfg.REDIS_DB, config),
        redis_name=providers.Callable(lambda cfg: cfg.REDIS_NAME, config),
    )

    cache_manager = providers.Singleton(
        RedisCacheManager,
        client=redis_client,
    )

    cache_service = providers.Singleton(
        CacheService,
        manager=cache_manager,
    )

    # ── Observability ─────────────────────────────────────────────────────────
    # Singleton — instrumentation registered once at startup

    observability = providers.Singleton(
        _make_observability,
        settings=config,
    )

    # ── LLM ───────────────────────────────────────────────────────────────────
    # Singleton — one authenticated client, shared across all tools

    llm_client = providers.Singleton(
        _make_llm_client,
        settings=config,
    )

    # ── MCP ───────────────────────────────────────────────────────────────────
    # Singleton — one MCP client, shared across all evaluation tools

    mcp_client = providers.Singleton(
        _make_mcp_client,
        settings=config,
    )

    # ── Knowledge store ───────────────────────────────────────────────────────

    knowledge_store = providers.Singleton(
        VertexKnowledgeStore,
        project=providers.Callable(lambda cfg: cfg.GCP_PROJECT, config),
        location=providers.Callable(lambda cfg: cfg.GCP_LOCATION, config),
        datastore_id=providers.Callable(lambda cfg: cfg.VERTEX_DATASTORE_ID, config),
    )

    # ── Prompt registry ───────────────────────────────────────────────────────

    prompt_registry = providers.Singleton(
        PhoenixPromptRegistry,
        mcp_client=mcp_client,
    )

    # ── Repositories ──────────────────────────────────────────────────────────
    # Factory — new instance per request, session_factory from db_engine

    patient_repository = providers.Factory(
        PatientRepository,
        session_factory=db_engine.provided.session,
    )

    intake_repository = providers.Factory(
        IntakeRepository,
        session_factory=db_engine.provided.session,
    )

    triage_result_repository = providers.Factory(
        TriageResultRepository,
        session_factory=db_engine.provided.session,
    )

    patient_brief_repository = providers.Factory(
        PatientBriefRepository,
        session_factory=db_engine.provided.session,
    )

    clinical_note_repository = providers.Factory(
        ClinicalNoteRepository,
        session_factory=db_engine.provided.session,
    )

    referral_repository = providers.Factory(
        ReferralLetterRepository,
        session_factory=db_engine.provided.session,
    )

    discharge_repository = providers.Factory(
        DischargeSummaryRepository,
        session_factory=db_engine.provided.session,
    )

    eval_score_repository = providers.Factory(
        EvalScoreRepository,
        session_factory=db_engine.provided.session,
    )

    prompt_improvement_repository = providers.Factory(
        PromptImprovementRepository,
        session_factory=db_engine.provided.session,
    )

    # ── Triage tools ──────────────────────────────────────────────────────────
    # Factory — improvement_notes fetched fresh per triage run

    urgency_score_tool = providers.Factory(
        UrgencyScoreTool,
        llm=llm_client,
        knowledge_store=knowledge_store,
    )

    differential_tool = providers.Factory(
        DifferentialDiagnosisTool,
        llm=llm_client,
        knowledge_store=knowledge_store,
    )

    drug_interaction_tool = providers.Factory(
        DrugInteractionTool,
        llm=llm_client,
        knowledge_store=knowledge_store,
    )

    assemble_brief_tool = providers.Factory(
        AssembleBriefTool,
        llm=llm_client,
    )

    # ── Documentation tools ───────────────────────────────────────────────────

    draft_note_tool = providers.Factory(
        DraftClinicalNoteTool,
        llm=llm_client,
    )

    draft_referral_tool = providers.Factory(
        DraftReferralTool,
        llm=llm_client,
    )

    draft_discharge_tool = providers.Factory(
        DraftDischargeTool,
        llm=llm_client,
    )

    # ── Evaluation tools ──────────────────────────────────────────────────────

    get_traces_tool = providers.Factory(
        GetTracesTool,
        mcp_client=mcp_client,
        project_name=providers.Callable(
            lambda cfg: cfg.PHOENIX_PROJECT_NAME, config
        ),
    )

    get_annotations_tool = providers.Factory(
        GetAnnotationsTool,
        mcp_client=mcp_client,
        project_name=providers.Callable(
            lambda cfg: cfg.PHOENIX_PROJECT_NAME, config
        ),
    )

    upsert_prompt_tool = providers.Factory(
        UpsertPromptTool,
        mcp_client=mcp_client,
    )

    # ── Agent factory ─────────────────────────────────────────────────────────
    # Singleton — assembles agents from injected tools

    agent_factory = providers.Singleton(
        ADKAgentFactory,
        model=providers.Callable(lambda cfg: cfg.GEMINI_MODEL, config),
        llm=llm_client,
        urgency_tool=urgency_score_tool,
        differential_tool=differential_tool,
        drug_tool=drug_interaction_tool,
        brief_tool=assemble_brief_tool,
        note_tool=draft_note_tool,
        referral_tool=draft_referral_tool,
        discharge_tool=draft_discharge_tool,
        get_traces_tool=get_traces_tool,
        get_annotations_tool=get_annotations_tool,
        upsert_prompt_tool=upsert_prompt_tool,
    )

    # ── Agents ────────────────────────────────────────────────────────────────
    # Factory — built fresh per request via agent_factory methods

    triage_agent = providers.Factory(
        providers.Callable(
            lambda factory: factory.build_triage_agent(),
            agent_factory,
        )
    )

    documentation_agent = providers.Factory(
        providers.Callable(
            lambda factory: factory.build_documentation_agent(),
            agent_factory,
        )
    )

    evaluator_agent = providers.Factory(
        providers.Callable(
            lambda factory: factory.build_evaluator_agent(),
            agent_factory,
        )
    )

    # ── Services ──────────────────────────────────────────────────────────────
    # Factory — receive repos and agents, new instance per request

    patient_service = providers.Factory(
        PatientService,
        patient_repo=patient_repository,
        intake_repo=intake_repository,
    )

    triage_service = providers.Factory(
        TriageService,
        triage_agent=triage_agent,
        triage_result_repo=triage_result_repository,
        brief_repo=patient_brief_repository,
        prompt_registry=prompt_registry,
    )

    documentation_service = providers.Factory(
        DocumentationService,
        documentation_agent=documentation_agent,
        note_tool=draft_note_tool,
        referral_tool=draft_referral_tool,
        discharge_tool=draft_discharge_tool,
        note_repo=clinical_note_repository,
        referral_repo=referral_repository,
        discharge_repo=discharge_repository,
    )

    evaluation_service = providers.Factory(
        EvaluationService,
        evaluator_agent=evaluator_agent,
        get_traces_tool=get_traces_tool,
        get_annotations_tool=get_annotations_tool,
        llm=llm_client,
        prompt_registry=prompt_registry,
        eval_score_repo=eval_score_repository,
        prompt_improvement_repo=prompt_improvement_repository,
        prompt_name=providers.Callable(
            lambda cfg: cfg.PHOENIX_TRIAGE_PROMPT_NAME, config
        ),
    )

    # ── Use cases ─────────────────────────────────────────────────────────────
    # Factory — receive services, new instance per request

    triage_patient_use_case = providers.Factory(
        TriagePatientUseCase,
        patient_service=patient_service,
        triage_service=triage_service,
    )

    generate_note_use_case = providers.Factory(
        GenerateNoteUseCase,
        documentation_service=documentation_service,
        patient_service=patient_service,
    )

    generate_referral_use_case = providers.Factory(
        GenerateReferralUseCase,
        documentation_service=documentation_service,
        patient_service=patient_service,
    )

    generate_discharge_use_case = providers.Factory(
        GenerateDischargeUseCase,
        documentation_service=documentation_service,
        patient_service=patient_service,
    )

    evaluate_agent_use_case = providers.Factory(
        EvaluateAgentUseCase,
        evaluation_service=evaluation_service,
    )