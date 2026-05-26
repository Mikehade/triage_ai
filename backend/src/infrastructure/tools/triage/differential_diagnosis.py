from src.core.tools.base import ITool
from src.domain.patient.value_objects import DifferentialDiagnosis
from src.domain.triage.service import IDifferentialDiagnosisTool
from src.infrastructure.language_models.base import ILLMClient, Message, MessageRole, LLMConfig
from src.infrastructure.knowledge.base import IKnowledgeStore
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical decision support assistant trained on Nigerian FMOH guidelines
and WHO protocols. Your task is to generate a ranked differential diagnosis list
for a patient presentation.

Consider the Nigerian disease burden: malaria, typhoid, tuberculosis, and other
endemic conditions must be appropriately weighted alongside global conditions.

You must respond with a valid JSON object in exactly this format:
{{
    "differentials": [
        {{
            "rank": 1,
            "condition": "<condition name>",
            "confidence": <float 0.0-1.0>,
            "reasoning": "<why this condition fits this presentation>",
            "distinguishing_questions": ["<question1>", "<question2>"],
            "icd10_code": "<ICD-10 code or null>"
        }}
    ]
}}

Return exactly 5 differentials ordered by likelihood. 
Do not include any text outside the JSON object.
"""

_USER_PROMPT = """
Patient:
- Chief complaint: {chief_complaint}
- Age: {age} years
- Sex: {sex}
- Symptom duration: {duration_hours} hours
- Additional history: {additional_history}

Relevant guidelines and disease patterns:
{guidelines}

Generate the differential diagnosis list.
"""


class DifferentialDiagnosisTool(IDifferentialDiagnosisTool, ITool):

    def __init__(self, llm: ILLMClient, knowledge_store: IKnowledgeStore):
        self._llm = llm
        self._knowledge_store = knowledge_store

    @property
    def name(self) -> str:
        return "differential_diagnosis"

    @property
    def description(self) -> str:
        return (
            "Generate a ranked differential diagnosis list for a patient presentation. "
            "Returns the top 5 most likely conditions with confidence scores, "
            "clinical reasoning, and distinguishing questions for each."
        )

    async def execute(
        self,
        chief_complaint: str,
        age: int,
        sex: str,
        symptom_duration_hours: int,
        additional_history: str | None = None,
    ) -> list[DifferentialDiagnosis]:
        try:
            guidelines = await self._knowledge_store.search(
                query=f"{chief_complaint} differential diagnosis Nigeria",
                top_k=5,
            )
            guidelines_text = "\n".join(
                f"- [{g['source']}]: {g['content']}"
                for g in guidelines
            )
        except Exception as e:
            logger.warning(f"Knowledge store unavailable: {e}")
            guidelines_text = "Guidelines unavailable."

        messages = [
            Message(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=_USER_PROMPT.format(
                    chief_complaint=chief_complaint,
                    age=age,
                    sex=sex,
                    duration_hours=symptom_duration_hours,
                    additional_history=additional_history or "None provided",
                    guidelines=guidelines_text,
                ),
            ),
        ]

        try:
            response = await self._llm.complete_json(
                messages=messages,
                config=LLMConfig(temperature=0.2),
            )

            return [
                DifferentialDiagnosis(
                    rank=d["rank"],
                    condition=d["condition"],
                    confidence=float(d["confidence"]),
                    reasoning=d["reasoning"],
                    distinguishing_questions=d.get("distinguishing_questions", []),
                    icd10_code=d.get("icd10_code"),
                )
                for d in response["differentials"]
            ]
        except (KeyError, ValueError) as e:
            logger.error(f"DifferentialDiagnosisTool: malformed LLM response: {e}")
            raise
        except Exception as e:
            logger.error(f"DifferentialDiagnosisTool.execute failed: {e}", exc_info=True)
            raise