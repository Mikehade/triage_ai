from __future__ import annotations

from src.infrastructure.knowledge.base import IKnowledgeStore
from utils.logger import get_logger

logger = get_logger()

# Minimal static content to keep tools functional without a real datastore.
# Expand these as you load real FMOH/WHO documents.
_STATIC_GUIDELINES = [
    {
        "content": (
            "Malaria: fever, chills, headache, myalgia. "
            "In Nigeria, Plasmodium falciparum is the predominant species. "
            "Severe malaria presents with altered consciousness, severe anaemia, "
            "respiratory distress, or hypoglycaemia — treat as urgent. "
            "First-line: artemether-lumefantrine for uncomplicated malaria."
        ),
        "source": "FMOH Nigeria Malaria Treatment Guidelines",
        "relevance": 1.0,
    },
    {
        "content": (
            "Typhoid fever: sustained fever, headache, abdominal pain, "
            "rose spots, relative bradycardia. "
            "Common in areas with poor sanitation. "
            "Complications: intestinal perforation, haemorrhage. "
            "First-line: ciprofloxacin or azithromycin."
        ),
        "source": "FMOH Nigeria Standard Treatment Guidelines",
        "relevance": 1.0,
    },
    {
        "content": (
            "Chest pain red flags: radiation to jaw or left arm, "
            "diaphoresis, nausea, dyspnoea — suspect ACS. "
            "Immediate ECG required. "
            "Troponin elevation confirms myocardial injury. "
            "Aspirin 300mg if STEMI suspected and no contraindications."
        ),
        "source": "WHO Cardiovascular Emergency Guidelines",
        "relevance": 1.0,
    },
    {
        "content": (
            "Tuberculosis: chronic cough >2 weeks, haemoptysis, "
            "night sweats, weight loss, fever. "
            "High index of suspicion in Nigeria given burden. "
            "Sputum AFB smear and GeneXpert for diagnosis. "
            "Notify public health authority on diagnosis."
        ),
        "source": "FMOH Nigeria TB Treatment Guidelines",
        "relevance": 1.0,
    },
    {
        "content": (
            "Sepsis: suspected infection + 2 or more SIRS criteria "
            "(temp >38°C or <36°C, HR >90, RR >20, WBC abnormal). "
            "Septic shock: sepsis + persistent hypotension despite fluids. "
            "Hour-1 bundle: blood cultures, broad-spectrum antibiotics, "
            "IV fluids 30ml/kg, lactate measurement."
        ),
        "source": "WHO Sepsis Management Guidelines",
        "relevance": 1.0,
    },
]

_STATIC_FORMULARY = [
    {
        "content": (
            "Warfarin + NSAIDs (ibuprofen, aspirin, diclofenac): "
            "increased bleeding risk. Severity: severe. "
            "Avoid combination — use paracetamol for analgesia instead."
        ),
        "source": "Nigeria National Drug Formulary",
        "relevance": 1.0,
    },
    {
        "content": (
            "Metformin + contrast agents: risk of lactic acidosis. "
            "Severity: moderate. "
            "Hold metformin 48 hours before and after contrast administration."
        ),
        "source": "Nigeria National Drug Formulary",
        "relevance": 1.0,
    },
    {
        "content": (
            "Artemether-lumefantrine + QT-prolonging drugs "
            "(haloperidol, erythromycin, amiodarone): "
            "additive QT prolongation risk. Severity: severe. "
            "ECG monitoring required — avoid if QTc >500ms."
        ),
        "source": "Nigeria National Drug Formulary",
        "relevance": 1.0,
    },
    {
        "content": (
            "Rifampicin + antiretrovirals (efavirenz, lopinavir): "
            "rifampicin induces CYP450 — significantly reduces ARV levels. "
            "Severity: severe. "
            "Use rifabutin-based regimen or adjust ARV doses per guidelines."
        ),
        "source": "FMOH Nigeria HIV/TB Co-infection Guidelines",
        "relevance": 1.0,
    },
]


class StaticKnowledgeStore(IKnowledgeStore):
    """
    Static in-memory knowledge store for local development and testing.

    Returns pre-loaded Nigerian clinical guidelines without any API calls.
    Swap in via the DI container by setting VERTEX_DATASTORE_ID="" or
    by overriding the knowledge_store provider in DevSettings container config.

    Extend _STATIC_GUIDELINES and _STATIC_FORMULARY as needed during development.
    """

    async def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Simple keyword match against static guidelines.
        Returns up to top_k results.
        """
        query_lower = query.lower()
        matched = [
            g for g in _STATIC_GUIDELINES
            if any(
                word in g["content"].lower()
                for word in query_lower.split()
                if len(word) > 3  # skip short words
            )
        ]

        # Fall back to all guidelines if no keyword match
        results = matched[:top_k] if matched else _STATIC_GUIDELINES[:top_k]

        logger.debug(
            f"StaticKnowledgeStore.search: "
            f"query='{query[:50]}' results={len(results)}"
        )
        return results

    async def get_drug_interactions(
        self,
        medications: list[str],
    ) -> list[dict]:
        """
        Keyword match against static formulary entries.
        """
        if not medications:
            return []

        medications_lower = [m.lower() for m in medications]
        matched = [
            f for f in _STATIC_FORMULARY