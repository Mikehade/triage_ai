from datetime import datetime, timezone
from uuid import uuid4, UUID

from src.core.tools.base import ITool
from src.domain.patient.value_objects import UrgencyLevel, DifferentialDiagnosis, DrugFlag
from src.domain.triage.entities import TriageResult, PatientBrief
from src.infrastructure.language_models.base import ILLMClient, Message, MessageRole, LLMConfig
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical assistant preparing a concise handoff brief for a doctor.
The doctor has 60 seconds to read this before walking into the consultation.

Write a 2-3 sentence plain-language summary of the patient's presentation,
urgency, and most likely diagnosis. Be direct. Avoid jargon where possible.
Use Nigerian clinical context — consider endemic diseases.

Respond with only the summary text. No JSON, no headers, no bullet points.
"""

_USER_PROMPT = """
Patient data:
- Chief complaint: {chief_complaint}
- Urgency: Level {urgency_level} ({urgency_label}) — {urgency_reasoning}
- Top diagnosis: {top_diagnosis} (confidence: {top_confidence:.0%})
- Red flags: {red_flags}
- Drug interaction flags: {drug_flags}

Write the 60-second handoff summary.
"""


class AssembleBriefTool(ITool):

    def __init__(self, llm: ILLMClient):
        self._llm = llm

    @property
    def name(self) -> str:
        return "assemble_brief"

    @property
    def description(self) -> str:
        return (
            "Assemble all triage tool outputs into a structured 60-second "
            "doctor handoff card. Returns a PatientBrief with urgency level, "
            "top differentials, drug flags, and a plain-language summary."
        )

    async def execute(
        self,
        triage_result: TriageResult,
        chief_complaint: str,
        improvement_notes: str | None = None,
    ) -> PatientBrief:
        top_differential = (
            triage_result.differentials[0]
            if triage_result.differentials
            else None
        )

        drug_flag_summary = None
        if triage_result.drug_flags:
            severe = [f for f in triage_result.drug_flags if f.severity == "severe"]
            if severe:
                drug_flag_summary = (
                    f"{len(severe)} severe interaction(s): "
                    + "; ".join(f"{f.drug_a} + {f.drug_b}" for f in severe)
                )
            else:
                drug_flag_summary = (
                    f"{len(triage_result.drug_flags)} interaction flag(s) — "
                    "review before prescribing"
                )

        messages = [
            Message(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=_USER_PROMPT.format(
                    chief_complaint=chief_complaint,
                    urgency_level=triage_result.urgency.level.value,
                    urgency_label=triage_result.urgency.level.label,
                    urgency_reasoning=triage_result.urgency.reasoning,
                    top_diagnosis=top_differential.condition if top_differential else "Unknown",
                    top_confidence=top_differential.confidence if top_differential else 0.0,
                    red_flags=", ".join(triage_result.urgency.red_flags) or "None",
                    drug_flags=drug_flag_summary or "None",
                ),
            ),
        ]

        try:
            response = await self._llm.complete(
                messages=messages,
                config=LLMConfig(temperature=0.3),
            )

            return PatientBrief(
                id=uuid4(),
                triage_result_id=triage_result.id,
                patient_id=triage_result.patient_id,
                urgency_level=triage_result.urgency.level,
                urgency_label=triage_result.urgency.level.label,
                summary=response.content.strip(),
                top_differentials=[
                    d.condition for d in triage_result.differentials[:3]
                ],
                drug_flag_summary=drug_flag_summary,
                red_flags=triage_result.urgency.red_flags,
                suggested_questions=(
                    triage_result.differentials[0].distinguishing_questions
                    if triage_result.differentials
                    else []
                ),
                assembled_at=datetime.now(timezone.utc),
                improvement_notes=improvement_notes,
            )
        except Exception as e:
            logger.error(f"AssembleBriefTool.execute failed: {e}", exc_info=True)
            raise