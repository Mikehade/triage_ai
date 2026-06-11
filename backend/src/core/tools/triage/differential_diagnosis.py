"""
Differential Diagnosis Tool.
Generates a ranked list of likely diagnoses for a patient presentation
using an LLM grounded in Nigerian FMOH and WHO clinical guidelines.
"""
from abc import abstractmethod

from src.core.tools.base import ITool
from src.domain.knowledge.service import IKnowledgeService
from src.domain.patient.value_objects import DifferentialDiagnosis
from src.infrastructure.language_models.base import ILLMClient, Message, MessageRole, LLMConfig
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical decision support assistant trained on Nigerian FMOH Standard 
Treatment Guidelines and WHO protocols. Your task is to generate a ranked 
differential diagnosis list for a patient presentation.

Consider the Nigerian disease burden — malaria, typhoid, tuberculosis, and 
sickle cell disease must always be considered for relevant presentations.

You must respond with a valid JSON object in exactly this format:
{{
    "differentials": [
        {{
            "rank": <integer starting at 1>,
            "condition": "<condition name>",
            "confidence": <float 0.0-1.0>,
            "reasoning": "<clinical reasoning>",
            "distinguishing_questions": ["<question1>", "<question2>"],
            "icd10_code": "<ICD-10 code or null>"
        }}
    ]
}}

Return at most 5 differentials ordered by likelihood.
Do not include any text outside the JSON object.
"""

_USER_PROMPT = """
Patient presentation:
- Chief complaint: {chief_complaint}
- Age: {age} years, {sex}
- Duration: {duration_hours} hours
- Additional history: {additional_history}

Relevant clinical guidelines:
{guidelines}

Generate the ranked differential diagnosis list.
"""


class IDifferentialDiagnosisTool(ITool):
    """
    Interface for the differential diagnosis tool.
    Exposed so the debug endpoint can depend on the abstraction.
    """

    @abstractmethod
    async def execute(
        self,
        chief_complaint: str,
        age: int,
        sex: str,
        symptom_duration_hours: int,
        additional_history: str | None = None,
    ) -> list[DifferentialDiagnosis]:
        raise NotImplementedError


class DifferentialDiagnosisTool(IDifferentialDiagnosisTool):

    def __init__(
        self,
        llm: ILLMClient,
        knowledge_service: IKnowledgeService,
    ):
        self._llm = llm
        self._knowledge_service = knowledge_service

    @property
    def name(self) -> str:
        return "differential_diagnosis"

    @property
    def description(self) -> str:
        return (
            "Generate a ranked differential diagnosis list for a patient presentation. "
            "Returns up to 5 conditions ordered by likelihood with clinical reasoning, "
            "distinguishing questions, and ICD-10 codes."
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
            guidelines = await self._knowledge_service.search(
                query=f"differential diagnosis {chief_complaint} {age} year old {sex}",
                top_k=5,
            )
            guidelines_text = "\n".join(
                f"- [{g['source']}]: {g['content']}"
                for g in guidelines
            )
        except Exception as e:
            logger.warning(
                f"DifferentialDiagnosisTool: knowledge service unavailable: {e}. "
                "Proceeding without guidelines."
            )
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
                config=LLMConfig(temperature=0.1),
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
                for d in response.get("differentials", [])
            ]
        except (KeyError, ValueError) as e:
            logger.error(f"DifferentialDiagnosisTool: malformed LLM response: {e}")
            raise
        except Exception as e:
            logger.error(f"DifferentialDiagnosisTool.execute failed: {e}", exc_info=True)
            raise