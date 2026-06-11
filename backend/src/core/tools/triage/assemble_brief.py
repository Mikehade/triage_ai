"""
Assemble Brief Tool.
Compiles all triage tool outputs into a concise doctor handoff card.
Returns a PatientBrief domain entity — does NOT persist it.
Persistence is the use case's responsibility, after the triage result
has been saved and a real triage_result_id exists in the database.
"""
from abc import abstractmethod
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.core.tools.base import ITool
from src.domain.triage.entities import TriageResult, PatientBrief
from src.infrastructure.language_models.base import ILLMClient, Message, MessageRole, LLMConfig
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical communication assistant. Your task is to compile a triage 
assessment into a concise 60-second handoff card for the attending doctor.

The brief must be clear, scannable, and actionable. The doctor should be able 
to understand the patient's situation in under one minute.

You must respond with a valid JSON object in exactly this format:
{{
    "urgency_label": "<human-readable urgency label>",
    "summary": "<2-3 sentence plain-language summary of the presentation>",
    "top_differentials": ["<condition1>", "<condition2>", "<condition3>"],
    "drug_flag_summary": "<one sentence summary of drug flags, or null if none>",
    "red_flags": ["<flag1>", "<flag2>"],
    "suggested_questions": ["<question1>", "<question2>", "<question3>"]
}}

Do not include any text outside the JSON object.
"""

_USER_PROMPT = """
Urgency level: {urgency_level} — {urgency_reasoning}
Red flags: {red_flags}

Top differentials:
{differentials}

Drug interaction flags:
{drug_flags}

Grounding sources used: {grounding_sources}

Compile the doctor handoff brief.
"""


class IAssembleBriefTool(ITool):
    """Interface for the assemble brief tool."""

    @abstractmethod
    async def execute(self, triage_result: TriageResult) -> PatientBrief:
        raise NotImplementedError


class AssembleBriefTool(IAssembleBriefTool):
    """
    Builds a PatientBrief from a TriageResult using an LLM.
    Does NOT persist — returns the entity for the caller to save
    after the triage result has been committed to the database.
    """

    def __init__(self, llm: ILLMClient):
        self._llm = llm

    @property
    def name(self) -> str:
        return "assemble_brief"

    @property
    def description(self) -> str:
        return (
            "Compile all triage outputs into a concise doctor handoff card. "
            "Summarises urgency, top differentials, drug flags, and suggested "
            "questions into a scannable 60-second brief."
        )

    async def execute(self, triage_result: TriageResult) -> PatientBrief:
        differentials_text = "\n".join(
            f"  {d.rank}. {d.condition} ({d.confidence:.0%}) — {d.reasoning}"
            for d in triage_result.differentials
        ) or "None identified."

        drug_flags_text = "\n".join(
            f"  - {f.drug_a} + {f.drug_b}: {f.severity} — {f.description}"
            for f in triage_result.drug_flags
        ) or "No interactions flagged."

        messages = [
            Message(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=_USER_PROMPT.format(
                    urgency_level=triage_result.urgency.level.label,
                    urgency_reasoning=triage_result.urgency.reasoning,
                    red_flags=", ".join(triage_result.urgency.red_flags) or "None",
                    differentials=differentials_text,
                    drug_flags=drug_flags_text,
                    grounding_sources=", ".join(triage_result.grounding_sources) or "None",
                ),
            ),
        ]

        try:
            response = await self._llm.complete_json(
                messages=messages,
                config=LLMConfig(temperature=0.2),
            )

            brief = PatientBrief(
                id=uuid4(),
                triage_result_id=triage_result.id,
                patient_id=triage_result.patient_id,
                urgency_level=triage_result.urgency.level,
                urgency_label=response["urgency_label"],
                summary=response["summary"],
                top_differentials=response.get("top_differentials", []),
                drug_flag_summary=response.get("drug_flag_summary"),
                red_flags=response.get("red_flags", []),
                suggested_questions=response.get("suggested_questions", []),
                assembled_at=datetime.now(timezone.utc),
            )

            logger.info(
                f"AssembleBriefTool: brief assembled "
                f"for patient {triage_result.patient_id}"
            )
            return brief

        except (KeyError, ValueError) as e:
            logger.error(f"AssembleBriefTool: malformed LLM response: {e}")
            raise
        except Exception as e:
            logger.error(f"AssembleBriefTool.execute failed: {e}", exc_info=True)
            raise