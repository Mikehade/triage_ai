from abc import ABC, abstractmethod


class IKnowledgeService(ABC):
    """
    Read-only interface for retrieving grounded clinical knowledge.
    Tools depend on this interface, not on IKnowledgeStore directly.
    Backed by VertexKnowledgeStore in production, static files locally.
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Semantic search over clinical knowledge base.

        Returns list of:
        {
            "content": str,
            "source": str,
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