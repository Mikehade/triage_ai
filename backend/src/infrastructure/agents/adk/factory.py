from src.infrastructure.agents.adk.triage_agent import ADKTriageAgent
from src.infrastructure.agents.adk.documentation_agent import ADKDocumentationAgent
from src.infrastructure.agents.adk.evaluator_agent import ADKEvaluatorAgent
from src.infrastructure.tools.triage.urgency_score import UrgencyScoreTool
from src.infrastructure.tools.triage.differential_diagnosis import DifferentialDiagnosisTool
from src.infrastructure.tools.triage.drug_interaction_check import DrugInteractionTool
from src.infrastructure.tools.triage.assemble_brief import AssembleBriefTool
from src.infrastructure.tools.documentation.draft_clinical_note import DraftClinicalNoteTool
from src.infrastructure.tools.documentation.draft_referral import DraftReferralTool
from src.infrastructure.tools.documentation.draft_discharge import DraftDischargeTool
from src.infrastructure.tools.evaluation.get_traces import GetTracesTool
from src.infrastructure.tools.evaluation.get_annotations import GetAnnotationsTool
from src.infrastructure.tools.evaluation.upsert_prompt import UpsertPromptTool
from src.infrastructure.language_models.base import ILLMClient


class ADKAgentFactory:
    """
    Assembles ADK agents from injected tool dependencies.

    The factory lives in the DI container as a Singleton.
    Each agent is built via a dedicated method — call only what you need.
    Tools are injected, never instantiated here.
    """

    def __init__(
        self,
        model: str,
        llm: ILLMClient,
        urgency_tool: UrgencyScoreTool,
        differential_tool: DifferentialDiagnosisTool,
        drug_tool: DrugInteractionTool,
        brief_tool: AssembleBriefTool,
        note_tool: DraftClinicalNoteTool,
        referral_tool: DraftReferralTool,
        discharge_tool: DraftDischargeTool,
        get_traces_tool: GetTracesTool,
        get_annotations_tool: GetAnnotationsTool,
        upsert_prompt_tool: UpsertPromptTool,
    ):
        self._model = model
        self._llm = llm
        self._urgency_tool = urgency_tool
        self._differential_tool = differential_tool
        self._drug_tool = drug_tool
        self._brief_tool = brief_tool
        self._note_tool = note_tool
        self._referral_tool = referral_tool
        self._discharge_tool = discharge_tool
        self._get_traces_tool = get_traces_tool
        self._get_annotations_tool = get_annotations_tool
        self._upsert_prompt_tool = upsert_prompt_tool

    def build_triage_agent(self) -> ADKTriageAgent:
        return ADKTriageAgent(
            model=self._model,
            urgency_tool=self._urgency_tool,
            differential_tool=self._differential_tool,
            drug_tool=self._drug_tool,
            brief_tool=self._brief_tool,
        )

    def build_documentation_agent(self) -> ADKDocumentationAgent:
        return ADKDocumentationAgent(
            model=self._model,
            note_tool=self._note_tool,
            referral_tool=self._referral_tool,
            discharge_tool=self._discharge_tool,
        )

    def build_evaluator_agent(self) -> ADKEvaluatorAgent:
        return ADKEvaluatorAgent(
            model=self._model,
            llm=self._llm,
            get_traces_tool=self._get_traces_tool,
            get_annotations_tool=self._get_annotations_tool,
            upsert_prompt_tool=self._upsert_prompt_tool,
        )