from src.core.tools.base import ITool
from src.domain.patient.value_objects import DrugFlag
from src.domain.triage.service import IDrugInteractionTool
from src.infrastructure.language_models.base import ILLMClient, Message, MessageRole, LLMConfig
from src.infrastructure.knowledge.base import IKnowledgeStore
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical pharmacology assistant. Your task is to check for drug 
interactions and contraindications between a patient's current medications 
and likely new prescriptions.

Reference the Nigerian National Drug Formulary and WHO Essential Medicines List.

You must respond with a valid JSON object in exactly this format:
{{
    "flags": [
        {{
            "drug_a": "<first drug name>",
            "drug_b": "<second drug name>",
            "severity": "mild|moderate|severe",
            "description": "<what the interaction causes>",
            "recommendation": "<what the prescriber should do>"
        }}
    ]
}}

If no interactions are found, return {{"flags": []}}.
Do not include any text outside the JSON object.
"""

_USER_PROMPT = """
Current medications: {current_medications}
Likely new prescriptions: {likely_prescriptions}

Formulary reference:
{formulary}

Check for interactions and contraindications.
"""


class DrugInteractionTool(IDrugInteractionTool, ITool):

    def __init__(self, llm: ILLMClient, knowledge_store: IKnowledgeStore):
        self._llm = llm
        self._knowledge_store = knowledge_store

    @property
    def name(self) -> str:
        return "drug_interaction_check"

    @property
    def description(self) -> str:
        return (
            "Check for drug interactions and contraindications between a patient's "
            "current medications and likely new prescriptions. "
            "Returns interaction flags with severity levels and recommendations."
        )

    async def execute(
        self,
        current_medications: list[str],
        likely_prescriptions: list[str],
    ) -> list[DrugFlag]:
        all_drugs = current_medications + likely_prescriptions

        if len(all_drugs) < 2:
            # Cannot have interactions with fewer than 2 drugs
            return []

        try:
            formulary_results = await self._knowledge_store.get_drug_interactions(
                medications=all_drugs,
            )
            formulary_text = "\n".join(
                f"- {r['content']}" for r in formulary_results
            )
        except Exception as e:
            logger.warning(f"Knowledge store unavailable for formulary lookup: {e}")
            formulary_text = "Formulary unavailable — use general pharmacology knowledge."

        messages = [
            Message(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=_USER_PROMPT.format(
                    current_medications=", ".join(current_medications) or "None",
                    likely_prescriptions=", ".join(likely_prescriptions) or "None",
                    formulary=formulary_text,
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
                for f in response.get("flags", [])
            ]
        except (KeyError, ValueError) as e:
            logger.error(f"DrugInteractionTool: malformed LLM response: {e}")
            raise
        except Exception as e:
            logger.error(f"DrugInteractionTool.execute failed: {e}", exc_info=True)
            raise