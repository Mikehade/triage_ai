from typing import Callable

from src.infrastructure.tools.triage.urgency_score import UrgencyScoreTool
from src.infrastructure.tools.triage.differential_diagnosis import DifferentialDiagnosisTool
from src.infrastructure.tools.triage.drug_interaction_check import DrugInteractionTool
from src.infrastructure.tools.triage.assemble_brief import AssembleBriefTool


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
        return {
            "differentials": [
                {
                    "rank": d.rank,
                    "condition": d.condition,
                    "confidence": d.confidence,
                    "reasoning": d.reasoning,
                    "distinguishing_questions": d.distinguishing_questions,
                    "icd10_code": d.icd10_code,
                }
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
        return {
            "flags": [
                {
                    "drug_a": f.drug_a,
                    "drug_b": f.drug_b,
                    "severity": f.severity,
                    "description": f.description,
                    "recommendation": f.recommendation,
                }
                for f in flags
            ],
            "flag_count": len(flags),
            "has_severe": any(f.severity == "severe" for f in flags),
        }

    return drug_interaction_check


def make_assemble_brief_tool(tool: AssembleBriefTool) -> Callable:
    async def assemble_brief(
        chief_complaint: str,
        urgency_level: int,
        urgency_reasoning: str,
        red_flags: list[str],
        differentials: list[dict],
        drug_flags: list[dict],
    ) -> dict:
        """
        Assemble all triage outputs into a structured 60-second doctor handoff card.
        Call this after urgency_score, differential_diagnosis, and drug_interaction_check
        have all completed. Do not call this tool before the others.

        Args:
            chief_complaint: The patient's primary complaint.
            urgency_level: Integer urgency level from urgency_score (1-5).
            urgency_reasoning: Reasoning string from urgency_score.
            red_flags: Red flag list from urgency_score.
            differentials: Differential list from differential_diagnosis.
            drug_flags: Drug flag list from drug_interaction_check.
        """
        from src.domain.patient.value_objects import UrgencyLevel, DifferentialDiagnosis, DrugFlag
        from src.domain.triage.entities import TriageResult, UrgencyScore
        from datetime import datetime, timezone
        from uuid import uuid4

        # Reconstruct domain objects from the dict inputs ADK passes
        urgency = UrgencyScore(
            level=UrgencyLevel(urgency_level),
            reasoning=urgency_reasoning,
            red_flags=red_flags,
            computed_at=datetime.now(timezone.utc),
        )

        differential_objs = [
            DifferentialDiagnosis(
                rank=d["rank"],
                condition=d["condition"],
                confidence=d["confidence"],
                reasoning=d["reasoning"],
                distinguishing_questions=d.get("distinguishing_questions", []),
                icd10_code=d.get("icd10_code"),
            )
            for d in differentials
        ]

        drug_flag_objs = [
            DrugFlag(
                drug_a=f["drug_a"],
                drug_b=f["drug_b"],
                severity=f["severity"],
                description=f["description"],
                recommendation=f["recommendation"],
            )
            for f in drug_flags
        ]

        # Minimal TriageResult for AssembleBriefTool
        triage_result = TriageResult(
            id=uuid4(),
            intake_id=uuid4(),
            patient_id=uuid4(),
            urgency=urgency,
            differentials=differential_objs,
            drug_flags=drug_flag_objs,
            grounding_sources=[],
            computed_at=datetime.now(timezone.utc),
        )

        brief = await tool.execute(
            triage_result=triage_result,
            chief_complaint=chief_complaint,
        )

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