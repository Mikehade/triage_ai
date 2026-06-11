import json
from typing import Callable
from uuid import UUID

from src.core.tools.triage.urgency_score import UrgencyScoreTool
from src.core.tools.triage.differential_diagnosis import DifferentialDiagnosisTool
from src.core.tools.triage.drug_interaction_check import DrugInteractionTool
from src.core.tools.triage.assemble_brief import AssembleBriefTool
from src.domain.triage.entities import PatientBrief


def make_urgency_score_tool(tool: UrgencyScoreTool) -> Callable:
    async def urgency_score(
        chief_complaint: str,
        symptom_duration_hours: int,
        vitals_summary: str | None = None,
        red_flag_symptoms: list[str] | None = None,
    ) -> dict:
        """
        Assess the clinical urgency of a patient presentation.
        Returns a triage level from 1 (routine) to 5 (critical),
        with clinical reasoning and red flag symptoms identified.

        Args:
            chief_complaint: The patient's primary complaint in their own words.
            symptom_duration_hours: How long the patient has had the symptoms.
            vitals_summary: Optional plain-text summary of recorded vitals.
            red_flag_symptoms: List of concerning symptoms already identified.
        """
        result = await tool.execute(
            chief_complaint=chief_complaint,
            symptom_duration_hours=symptom_duration_hours,
            vitals_summary=vitals_summary,
            red_flag_symptoms=red_flag_symptoms or [],
        )
        return {
            "level": result.level.value,
            "label": result.level.label,
            "reasoning": result.reasoning,
            "red_flags": result.red_flags,
            "should_flag": result.level.should_flag,
        }

    return urgency_score


def make_differential_diagnosis_tool(tool: DifferentialDiagnosisTool) -> Callable:
    async def differential_diagnosis(
        chief_complaint: str,
        age: int,
        sex: str,
        symptom_duration_hours: int,
        additional_history: str | None = None,
    ) -> dict:
        """
        Generate a ranked differential diagnosis list for a patient presentation.
        Returns the top 5 most likely conditions with confidence scores,
        clinical reasoning grounded in Nigerian FMOH guidelines,
        and distinguishing questions for each condition.

        Args:
            chief_complaint: The patient's primary complaint.
            age: Patient age in years.
            sex: Patient sex (male/female/other).
            symptom_duration_hours: Duration of symptoms in hours.
            additional_history: Any additional relevant history.
        """
        results = await tool.execute(
            chief_complaint=chief_complaint,
            age=age,
            sex=sex,
            symptom_duration_hours=symptom_duration_hours,
            additional_history=additional_history,
        )
        # Serialise each differential to a JSON string.
        # Gemini rejects list[dict] parameters due to additionalProperties
        # in the generated schema — list[str] is safe and unambiguous.
        return {
            "differentials_json": [
                json.dumps({
                    "rank": d.rank,
                    "condition": d.condition,
                    "confidence": d.confidence,
                    "reasoning": d.reasoning,
                    "distinguishing_questions": d.distinguishing_questions,
                    "icd10_code": d.icd10_code,
                })
                for d in results
            ],
            "count": len(results),
        }

    return differential_diagnosis


def make_drug_interaction_tool(tool: DrugInteractionTool) -> Callable:
    async def drug_interaction_check(
        current_medications: list[str],
        likely_prescriptions: list[str] | None = None,
    ) -> dict:
        """
        Check for drug interactions and contraindications between a patient's
        current medications and likely new prescriptions.
        References the Nigerian National Drug Formulary and WHO Essential Medicines List.

        Args:
            current_medications: Medications the patient is currently taking.
            likely_prescriptions: Medications likely to be prescribed in this consultation.
        """
        flags = await tool.execute(
            current_medications=current_medications,
            likely_prescriptions=likely_prescriptions or [],
        )
        # Serialise each flag to a JSON string — same reason as differentials.
        return {
            "drug_flags_json": [
                json.dumps({
                    "drug_a": f.drug_a,
                    "drug_b": f.drug_b,
                    "severity": f.severity,
                    "description": f.description,
                    "recommendation": f.recommendation,
                })
                for f in flags
            ],
            "flag_count": len(flags),
            "has_severe": any(f.severity == "severe" for f in flags),
        }

    return drug_interaction_check


def make_assemble_brief_tool(
    tool: AssembleBriefTool,
    patient_id: UUID,
    intake_id: UUID,
    brief_sink: list,
) -> Callable:
    """
    patient_id and intake_id are closed over from the agent instance.
    brief_sink is a single-element list used as a mutable container so
    the assembled PatientBrief can be retrieved by the use case after
    the agent run completes — without any DB write happening inside the tool.

    Sequence enforced by the use case:
      1. agent.run() → assemble_brief → brief_sink[0] = brief
      2. triage_service.save_result(triage_result)   ← triage_result_id committed
      3. triage_service.save_brief(brief_sink[0])    ← FK satisfied
    """
    async def assemble_brief(
        urgency_level: int,
        urgency_reasoning: str,
        red_flags: list[str],
        differentials_json: list[str],
        drug_flags_json: list[str],
        grounding_sources: list[str] | None = None,
    ) -> dict:
        """
        Assemble all triage outputs into a structured 60-second doctor handoff card.
        Call this after urgency_score, differential_diagnosis, and drug_interaction_check
        have all completed. Do not call this tool before the others.

        Pass differentials_json from differential_diagnosis output.
        Pass drug_flags_json from drug_interaction_check output.

        Args:
            urgency_level: Integer urgency level from urgency_score (1-5).
            urgency_reasoning: Reasoning string from urgency_score.
            red_flags: Red flag list from urgency_score.
            differentials_json: JSON-serialised differential list from differential_diagnosis.
            drug_flags_json: JSON-serialised drug flag list from drug_interaction_check.
            grounding_sources: Optional list of knowledge sources cited.
        """
        from datetime import datetime, timezone
        from uuid import uuid4

        from src.domain.patient.value_objects import UrgencyLevel, DifferentialDiagnosis, DrugFlag
        from src.domain.triage.entities import TriageResult, UrgencyScore

        urgency = UrgencyScore(
            level=UrgencyLevel(urgency_level),
            reasoning=urgency_reasoning,
            red_flags=red_flags or [],
            computed_at=datetime.now(timezone.utc),
        )

        differential_objs = []
        for item in (differentials_json or []):
            try:
                d = json.loads(item) if isinstance(item, str) else item
                differential_objs.append(DifferentialDiagnosis(
                    rank=d.get("rank"),
                    condition=d.get("condition"),
                    confidence=float(d.get("confidence", 0.0)),
                    reasoning=d.get("reasoning", ""),
                    distinguishing_questions=d.get("distinguishing_questions", []),
                    icd10_code=d.get("icd10_code"),
                ))
            except (json.JSONDecodeError, TypeError):
                continue

        drug_flag_objs = []
        for item in (drug_flags_json or []):
            try:
                f = json.loads(item) if isinstance(item, str) else item
                drug_flag_objs.append(DrugFlag(
                    drug_a=f.get("drug_a", ""),
                    drug_b=f.get("drug_b", ""),
                    severity=f.get("severity", "mild"),
                    description=f.get("description", ""),
                    recommendation=f.get("recommendation", ""),
                ))
            except (json.JSONDecodeError, TypeError):
                continue

        # Build a transient TriageResult for the brief assembly LLM call.
        # This is NOT persisted — the real triage_result_id is injected
        # by the use case after save_result() commits the real record.
        transient_result = TriageResult(
            id=uuid4(),          # placeholder — overwritten by use case
            intake_id=intake_id,
            patient_id=patient_id,
            urgency=urgency,
            differentials=differential_objs,
            drug_flags=drug_flag_objs,
            grounding_sources=grounding_sources or [],
            computed_at=datetime.now(timezone.utc),
        )

        # Tool returns PatientBrief but does NOT persist it.
        brief: PatientBrief = await tool.execute(triage_result=transient_result)

        # Store in sink so use case can retrieve it after persisting triage_result.
        brief_sink.clear()
        brief_sink.append(brief)

        return {
            "urgency_level": brief.urgency_level.value,
            "urgency_label": brief.urgency_label,
            "summary": brief.summary,
            "top_differentials": brief.top_differentials,
            "drug_flag_summary": brief.drug_flag_summary,
            "red_flags": brief.red_flags,
            "suggested_questions": brief.suggested_questions,
        }

    return assemble_brief