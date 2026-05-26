from __future__ import annotations
from abc import ABC, abstractmethod


class IKnowledgeStore(ABC):
    """
    Interface for retrieving grounded clinical knowledge.
    Backed by Vertex AI Search in production, static files locally.
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Returns list of:
        {
            "content": str,
            "source": str,      # document name / URL
            "relevance": float
        }
        """
        raise NotImplementedError

    @abstractmethod
    async def get_drug_interactions(
        self,
        medications: list[str],
    ) -> list[dict]:
        """
        Direct formulary lookup — bypasses semantic search.
        Returns known interaction records for the given drug list.
        """
        raise NotImplementedError