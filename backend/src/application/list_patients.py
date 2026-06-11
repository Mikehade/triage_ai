"""
List Patients Use Case.
Fetches a paginated list of active patients and optionally enriches each
with triage result and brief using concurrent lookups.
"""
import asyncio
from dataclasses import dataclass

from src.application.patient_detail import PatientDetail
from src.domain.patient.entities import Patient
from src.domain.patient.service import IPatientService, PatientPage
from src.domain.triage.service import ITriageService
from utils.logger import get_logger

logger = get_logger()


@dataclass
class PatientListResult:
    patients: list[PatientDetail]
    total: int
    page: int
    page_size: int
    total_pages: int


class ListPatientsUseCase:
    """
    Lists active patients with pagination and optional triage/brief enrichment.

    When enrichment is requested, all triage/brief lookups fire concurrently
    via asyncio.gather — latency is the slowest single lookup, not the sum.
    """

    def __init__(
        self,
        patient_service: IPatientService,
        triage_service: ITriageService,
    ):
        self._patient_service = patient_service
        self._triage_service = triage_service

    async def execute(
        self,
        page: int = 1,
        page_size: int = 50,
        include_triage: bool = False,
        include_brief: bool = False,
    ) -> PatientListResult:
        """
        Fetch a page of active patients with optional enrichment.

        Args:
            page:           1-based page number.
            page_size:      Records per page. Clamped to 1–100 by service.
            include_triage: Attach the most recent triage result per patient.
            include_brief:  Attach the assembled brief per patient.
                            Ignored if include_triage is False.

        Returns:
            PatientListResult with enriched PatientDetail records and
            full pagination metadata.

        Raises:
            Exception: On any database error in the patient fetch.
        """
        patient_page: PatientPage = await self._patient_service.list_active_patients(
            page=page,
            page_size=page_size,
        )

        if not patient_page.patients:
            return PatientListResult(
                patients=[],
                total=patient_page.total,
                page=patient_page.page,
                page_size=patient_page.page_size,
                total_pages=patient_page.total_pages,
            )

        if not include_triage:
            return PatientListResult(
                patients=[PatientDetail(patient=p) for p in patient_page.patients],
                total=patient_page.total,
                page=patient_page.page,
                page_size=patient_page.page_size,
                total_pages=patient_page.total_pages,
            )

        details = await self._enrich_concurrent(
            patients=patient_page.patients,
            include_brief=include_brief,
        )

        logger.info(
            f"ListPatientsUseCase: page={page} page_size={page_size} "
            f"returned {len(details)}/{patient_page.total} "
            f"include_triage={include_triage} include_brief={include_brief}"
        )

        return PatientListResult(
            patients=details,
            total=patient_page.total,
            page=patient_page.page,
            page_size=patient_page.page_size,
            total_pages=patient_page.total_pages,
        )

    async def _enrich_concurrent(
        self,
        patients: list[Patient],
        include_brief: bool,
    ) -> list[PatientDetail]:
        """
        Fetch triage results and briefs for all patients concurrently.
        Individual failures are caught per-patient — one bad record
        does not prevent the rest from being returned.
        """
        async def enrich_one(patient: Patient) -> PatientDetail:
            triage_result = None
            brief = None

            try:
                triage_result = await self._triage_service.get_result(patient.id)
            except Exception as e:
                logger.warning(
                    f"ListPatientsUseCase: triage fetch failed "
                    f"for patient {patient.id}: {e}"
                )

            if include_brief and triage_result:
                try:
                    brief = await self._triage_service.get_brief(patient.id)
                except Exception as e:
                    logger.warning(
                        f"ListPatientsUseCase: brief fetch failed "
                        f"for patient {patient.id}: {e}"
                    )

            return PatientDetail(
                patient=patient,
                triage_result=triage_result,
                brief=brief,
            )

        return list(await asyncio.gather(*[enrich_one(p) for p in patients]))