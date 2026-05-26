from typing import Callable
from uuid import UUID

from src.infrastructure.tools.documentation.draft_clinical_note import DraftClinicalNoteTool
from src.infrastructure.tools.documentation.draft_referral import DraftReferralTool
from src.infrastructure.tools.documentation.draft_discharge import DraftDischargeTool


def make_draft_note_tool(tool: DraftClinicalNoteTool) -> Callable:
    async def draft_clinical_note(
        patient_id: str,
        triage_result_id: str,
        transcript: str | None = None,
        doctor_additions: str | None = None,
    ) -> dict:
        """
        Draft a structured SOAP clinical note from a consultation transcript.
        The note is pre-filled for doctor review — the doctor edits and signs.

        Args:
            patient_id: UUID string of the patient.
            triage_result_id: UUID string of the triage result for this consultation.
            transcript: Ambient consultation transcript text.
            doctor_additions: Any additional notes the doctor wants included.
        """
        note = await tool.execute(
            patient_id=UUID(patient_id),
            triage_result_id=UUID(triage_result_id),
            transcript=transcript,
            doctor_additions=doctor_additions,
        )
        return {
            "id": str(note.id),
            "subjective": note.subjective,
            "objective": note.objective,
            "assessment": note.assessment,
            "plan": note.plan,
            "doctor_signed": note.doctor_signed,
        }

    return draft_clinical_note


def make_draft_referral_tool(tool: DraftReferralTool) -> Callable:
    async def draft_referral(
        clinical_note_id: str,
        receiving_facility: str,
        reason: str,
        note_summary: str = "",
    ) -> dict:
        """
        Draft a formal referral letter to a receiving facility.
        Returns the letter body for doctor review and sign-off.

        Args:
            clinical_note_id: UUID string of the clinical note.
            receiving_facility: Name of the facility receiving the referral.
            reason: Clinical reason for the referral.
            note_summary: Brief summary of the clinical note assessment and plan.
        """
        referral = await tool.execute(
            clinical_note_id=UUID(clinical_note_id),
            receiving_facility=receiving_facility,
            reason=reason,
            note_summary=note_summary,
        )
        return {
            "id": str(referral.id),
            "receiving_facility": referral.receiving_facility,
            "reason": referral.reason,
            "body": referral.body,
        }

    return draft_referral


def make_draft_discharge_tool(tool: DraftDischargeTool) -> Callable:
    async def draft_discharge(
        clinical_note_id: str,
        medications: list[str],
        diagnosis: str = "",
        note_summary: str = "",
        follow_up: str | None = None,
    ) -> dict:
        """
        Draft a plain-language discharge summary for the patient and their family.
        Avoids medical jargon — written to be understood without clinical training.

        Args:
            clinical_note_id: UUID string of the clinical note.
            medications: List of medications being prescribed at discharge.
            diagnosis: Primary diagnosis in plain language.
            note_summary: Summary from the clinical note assessment.
            follow_up: Follow-up instructions (when and where).
        """
        discharge = await tool.execute(
            clinical_note_id=UUID(clinical_note_id),
            medications=medications,
            follow_up=follow_up,
            diagnosis=diagnosis,
            note_summary=note_summary,
        )
        return {
            "id": str(discharge.id),
            "diagnosis": discharge.diagnosis,
            "medications": discharge.medications,
            "instructions": discharge.instructions,
            "follow_up": discharge.follow_up,
        }

    return draft_discharge