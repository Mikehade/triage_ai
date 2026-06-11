"""
Drug Interaction Check Tool.
Checks for clinically significant interactions between a patient's
current medications and likely prescriptions using the formulary
knowledge service and LLM reasoning.
"""
from abc import abstractmethod

from src.core.tools.base import ITool
from src.domain.knowledge.service import IKnowledgeService
from src.domain.patient.value_objects import DrugFlag
from src.infrastructure.language_models.base import ILLMClient, Message, MessageRole, LLMConfig
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical pharmacology assistant. Your task is to identify clinically 
significant drug interactions between a patient's current medications and 
likely new prescriptions based on their diagnosis.

Severity levels:
- mild: Monitor only, unlikely to cause significant harm
- moderate: Use with caution, may require dose adjustment or monitoring
- severe: Avoid combination, significant risk of harm

You must respond with a valid JSON object in exactly this format:
{{
    "drug_flags": [
        {{
            "drug_a": "<medication name>",
            "drug_b": "<medication name>",
            "severity": "<mild|moderate|severe>",
            "description": "<description of the interaction>",
            "recommendation": "<clinical recommendation>"
        }}
    ]
}}

If no interactions are found, return an empty drug_flags list.
Do not include any text outside the JSON object.
"""

_USER_PROMPT = """
Current medications: {current_medications}
Likely new prescriptions: {likely_prescriptions}

Known interaction records from formulary:
{interaction_records}

Identify all clinically significant interactions.
"""


class IDrugInteractionTool(ITool):
    """
    Interface for the drug interaction check tool.
    Exposed so the debug endpoint can depend on the abstraction.
    """

    @abstractmethod
    async def execute(
        self,
        current_medications: list[str],
        likely_prescriptions: list[str],
    ) -> list[DrugFlag]:
        raise NotImplementedError


class DrugInteractionTool(IDrugInteractionTool):

    def __init__(
        self,
        llm: ILLMClient,
        knowledge_service: IKnowledgeService,
    ):
        self._llm = llm
        self._knowledge_service = knowledge_service

    @property
    def name(self) -> str:
        return "drug_interaction_check"

    @property
    def description(self) -> str:
        return (
            "Check for clinically significant interactions between a patient's "
            "current medications and likely new prescriptions. "
            "Returns flagged interactions with severity and recommendations."
        )

    async def execute(
        self,
        current_medications: list[str],
        likely_prescriptions: list[str],
    ) -> list[DrugFlag]:
        all_medications = current_medications + likely_prescriptions

        try:
            interaction_records = await self._knowledge_service.get_drug_interactions(
                medications=all_medications,
            )
            records_text = "\n".join(
                f"- {r.get('description', str(r))}"
                for r in interaction_records
            ) or "No records found in formulary."
        except Exception as e:
            logger.warning(
                f"DrugInteractionTool: knowledge service unavailable: {e}. "
                "Proceeding with LLM knowledge only."
            )
            records_text = "Formulary unavailable — use general pharmacology knowledge."

        messages = [
            Message(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=_USER_PROMPT.format(
                    current_medications=", ".join(current_medications) or "None",
                    likely_prescriptions=", ".join(likely_prescriptions) or "None",
                    interaction_records=records_text,
                ),
            ),
        ]

        try:
            response = await self._llm.complete_json(
                messages=messages,
                config=LLMConfig(temperature=0.1),
            )

            return [
                DrugFlag(
                    drug_a=f["drug_a"],
                    drug_b=f["drug_b"],
                    severity=f["severity"],
                    description=f["description"],
                    recommendation=f["recommendation"],
                )
                for f in response.get("drug_flags", [])
            ]
        except (KeyError, ValueError) as e:
            logger.error(f"DrugInteractionTool: malformed LLM response: {e}")
            raise
        except Exception as e:
            logger.error(f"DrugInteractionTool.execute failed: {e}", exc_info=True)
            raise