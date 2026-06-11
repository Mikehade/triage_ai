"""
Dependency Injection Container.
Wires the full application graph — infrastructure up through use cases.

Dependency direction enforced here:
  Repository ← Service ← Use Case ← Router
  Tool ← Agent ← Use Case
  KnowledgeService ← Tool
  PromptRegistry ← Use Case
"""
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

# MCP
from src.infrastructure.mcp.phoenix_mcp import PhoenixMCPClient
from src.infrastructure.mcp.noop_mcp import NoopMCPClient
from src.infrastructure.mcp.prompt_registry import PhoenixPromptRegistry

# Observability
from src.infrastructure.observability.phoenix import PhoenixObservability
from src.infrastructure.observability.noop import NoopObservability

# Knowledge
from src.infrastructure.knowledge.vertex_datastore import VertexKnowledgeStore
from src.infrastructure.knowledge.knowledge_service import KnowledgeService

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

# Tools — triage (core)
from src.core.tools.triage.urgency_score import UrgencyScoreTool
from src.core.tools.triage.differential_diagnosis import DifferentialDiagnosisTool
from src.core.tools.triage.drug_interaction_check import DrugInteractionTool
from src.core.tools.triage.assemble_brief import AssembleBriefTool

# Tools — documentation (core)
from src.core.tools.documentation.draft_clinical_note import DraftClinicalNoteTool
from src.core.tools.documentation.draft_referral import DraftReferralTool
from src.core.tools.documentation.draft_discharge import DraftDischargeTool

# Tools — evaluation (infrastructure — depend on MCP)
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
from src.application.get_patient import GetPatientUseCase
from src.application.list_patients import ListPatientsUseCase


def _make_mcp_client(settings) -> PhoenixMCPClient | NoopMCPClient:
    if settings.PHOENIX_MODE == "noop":
        return NoopMCPClient()
    return PhoenixMCPClient(
        api_key=settings.PHOENIX_API_KEY,
        collector_endpoint=settings.phoenix_endpoint,
        project_name=settings.PHOENIX_PROJECT_NAME,
    )


def _make_observability(settings) -> PhoenixObservability | NoopObservability:
    if settings.PHOENIX_MODE == "noop":
        return NoopObservability()
    return PhoenixObservability(
        project_name=settings.PHOENIX_PROJECT_NAME,
        endpoint=settings.phoenix_endpoint,
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

    observability = providers.Singleton(
        _make_observability,
        settings=config,
    )

    # ── LLM ───────────────────────────────────────────────────────────────────

    llm_client = providers.Singleton(
        GeminiClient,
        api_key=providers.Callable(lambda cfg: cfg.GEMINI_API_KEY, config),
        model=providers.Callable(lambda cfg: cfg.GEMINI_MODEL, config),
    )

    # ── MCP ───────────────────────────────────────────────────────────────────

    mcp_client = providers.Singleton(
        _make_mcp_client,
        settings=config,
    )

    # ── Knowledge ─────────────────────────────────────────────────────────────
    # Singleton — one authenticated datastore client shared across all tools

    knowledge_store = providers.Singleton(
        VertexKnowledgeStore,
        project=providers.Callable(lambda cfg: cfg.GCP_PROJECT, config),
        location=providers.Callable(lambda cfg: cfg.GCP_LOCATION, config),
        datastore_id=providers.Callable(lambda cfg: cfg.VERTEX_DATASTORE_ID, config),
    )

    knowledge_service = providers.Singleton(
        KnowledgeService,
        knowledge_store=knowledge_store,
    )

    # ── Prompt registry ───────────────────────────────────────────────────────

    prompt_registry = providers.Singleton(
        PhoenixPromptRegistry,
        mcp_client=mcp_client,
    )

    # ── Repositories ──────────────────────────────────────────────────────────
    # Factory — fresh session per request

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

    # ── Services ──────────────────────────────────────────────────────────────
    # Factory — pure repo wrappers, no agents or tools

    patient_service = providers.Factory(
        PatientService,
        patient_repo=patient_repository,
        intake_repo=intake_repository,
    )

    triage_service = providers.Factory(
        TriageService,
        triage_result_repo=triage_result_repository,
        brief_repo=patient_brief_repository,
    )

    documentation_service = providers.Factory(
        DocumentationService,
        note_repo=clinical_note_repository,
        referral_repo=referral_repository,
        discharge_repo=discharge_repository,
    )

    evaluation_service = providers.Factory(
        EvaluationService,
        eval_score_repo=eval_score_repository,
        prompt_improvement_repo=prompt_improvement_repository,
    )

    # ── Triage tools ──────────────────────────────────────────────────────────
    # Factory — built fresh per request
    # AssembleBriefTool takes triage_service to persist the brief it produces

    urgency_score_tool = providers.Factory(
        UrgencyScoreTool,
        llm=llm_client,
        knowledge_service=knowledge_service,
    )

    differential_tool = providers.Factory(
        DifferentialDiagnosisTool,
        llm=llm_client,
        knowledge_service=knowledge_service,
    )

    drug_interaction_tool = providers.Factory(
        DrugInteractionTool,
        llm=llm_client,
        knowledge_service=knowledge_service,
    )

    assemble_brief_tool = providers.Factory(
        AssembleBriefTool,
        llm=llm_client,
        # triage_service=triage_service,
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
    # Factory — built fresh per request via agent_factory

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

    # ── Use cases ─────────────────────────────────────────────────────────────
    # Factory — own orchestration, receive agents + services

    triage_patient_use_case = providers.Factory(
        TriagePatientUseCase,
        triage_agent=triage_agent,
        prompt_registry=prompt_registry,
        patient_service=patient_service,
        triage_service=triage_service,
    )

    get_patient_use_case = providers.Factory(
        GetPatientUseCase,
        patient_service=patient_service,
        triage_service=triage_service,
    )
 
    list_patients_use_case = providers.Factory(
        ListPatientsUseCase,
        patient_service=patient_service,
        triage_service=triage_service,
    )
    

    generate_note_use_case = providers.Factory(
        GenerateNoteUseCase,
        note_tool=draft_note_tool,
        documentation_service=documentation_service,
        patient_service=patient_service,
    )

    generate_referral_use_case = providers.Factory(
        GenerateReferralUseCase,
        referral_tool=draft_referral_tool,
        documentation_service=documentation_service,
        patient_service=patient_service,
    )

    generate_discharge_use_case = providers.Factory(
        GenerateDischargeUseCase,
        discharge_tool=draft_discharge_tool,
        documentation_service=documentation_service,
        patient_service=patient_service,
    )

    evaluate_agent_use_case = providers.Factory(
        EvaluateAgentUseCase,
        llm=llm_client,
        get_traces_tool=get_traces_tool,
        get_annotations_tool=get_annotations_tool,
        prompt_registry=prompt_registry,
        evaluation_service=evaluation_service,
        prompt_name=providers.Callable(
            lambda cfg: cfg.PHOENIX_TRIAGE_PROMPT_NAME, config
        ),
    )