from datetime import datetime, timezone

from src.core.tools.base import ITool
from src.domain.patient.value_objects import UrgencyLevel
from src.domain.triage.entities import UrgencyScore
from src.domain.triage.service import IUrgencyScoreTool
from src.infrastructure.language_models.base import ILLMClient, Message, MessageRole, LLMConfig
from src.infrastructure.knowledge.base import IKnowledgeStore
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical triage assistant trained on Nigerian FMOH Standard Treatment 
Guidelines and WHO protocols. Your task is to assess the urgency of a patient 
presentation and assign a triage level.

Urgency levels:
1 - ROUTINE: Non-urgent, can wait. No immediate risk.
2 - LOW: Should be seen today but not immediately.
3 - MODERATE: Should be seen within 1-2 hours.
4 - HIGH: Should be seen within 30 minutes. Potential for deterioration.
5 - CRITICAL: Immediate threat to life. See now.

You must respond with a valid JSON object in exactly this format:
{{
    "level": <integer 1-5>,
    "reasoning": "<clear clinical reasoning for this level>",
    "red_flags": ["<flag1>", "<flag2>"]
}}

Red flags are specific symptoms or findings that elevated the score.
If no red flags, return an empty list.
Do not include any text outside the JSON object.
"""

_USER_PROMPT = """
Patient presentation:
- Chief complaint: {chief_complaint}
- Duration: {duration_hours} hours
- Vitals summary: {vitals_summary}
- Reported red flag symptoms: {red_flags}

Relevant clinical guidelines:
{guidelines}

{improvement_notes}

Assess urgency and respond with the required JSON.
"""


class UrgencyScoreTool(IUrgencyScoreTool, ITool):

    def __init__(
        self,
        llm: ILLMClient,
        knowledge_store: IKnowledgeStore,
        improvement_notes: str | None = None,
    ):
        self._llm = llm
        self._knowledge_store = knowledge_store
        self._improvement_notes = improvement_notes or ""

    @property
    def name(self) -> str:
        return "urgency_score"

    @property
    def description(self) -> str:
        return (
            "Assess the clinical urgency of a patient presentation and assign "
            "a triage level from 1 (routine) to 5 (critical). "
            "Returns the urgency level, clinical reasoning, and red flag symptoms."
        )

    async def execute(
        self,
        chief_complaint: str,
        symptom_duration_hours: int,
        vitals_summary: str | None = None,
        red_flag_symptoms: list[str] | None = None,
    ) -> UrgencyScore:
        red_flag_symptoms = red_flag_symptoms or []
        vitals_text = vitals_summary or "Not provided"

        # Retrieve relevant guidelines from knowledge store
        try:
            guidelines = await self._knowledge_store.search(
                query=f"triage urgency {chief_complaint}",
                top_k=3,
            )
            guidelines_text = "\n".join(
                f"- [{g['source']}]: {g['content']}"
                for g in guidelines
            )
        except Exception as e:
            logger.warning(f"Knowledge store unavailable: {e}. Proceeding without guidelines.")
            guidelines_text = "Guidelines unavailable."

        improvement_section = (
            f"Additional guidance from self-improvement loop:\n{self._improvement_notes}"
            if self._improvement_notes
            else ""
        )

        messages = [
            Message(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=_USER_PROMPT.format(
                    chief_complaint=chief_complaint,
                    duration_hours=symptom_duration_hours,
                    vitals_summary=vitals_text,
                    red_flags=", ".join(red_flag_symptoms) or "None reported",
                    guidelines=guidelines_text,
                    improvement_notes=improvement_section,
                ),
            ),
        ]

        try:
            response = await self._llm.complete_json(
                messages=messages,
                config=LLMConfig(temperature=0.1),
            )

            level_int = int(response["level"])
            if level_int not in range(1, 6):
                raise ValueError(f"Invalid urgency level: {level_int}")

            return UrgencyScore(
                level=UrgencyLevel(level_int),
                reasoning=response["reasoning"],
                red_flags=response.get("red_flags", []),
                computed_at=datetime.now(timezone.utc),
            )
        except (KeyError, ValueError) as e:
            logger.error(f"UrgencyScoreTool: malformed LLM response: {e}")
            raise
        except Exception as e:
            logger.error(f"UrgencyScoreTool.execute failed: {e}", exc_info=True)
            raise