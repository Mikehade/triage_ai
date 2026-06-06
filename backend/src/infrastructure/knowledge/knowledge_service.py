"""
Knowledge Service.
Implements IKnowledgeService over the Vertex AI Search datastore.
Tools depend on IKnowledgeService — never on IKnowledgeStore directly.
"""
from src.domain.knowledge.service import IKnowledgeService
from src.infrastructure.knowledge.base import IKnowledgeStore
from utils.logger import get_logger

logger = get_logger()


class KnowledgeService(IKnowledgeService):
    """
    Thin adapter over IKnowledgeStore.
    Provides the interface tools depend on while keeping the
    Vertex AI implementation detail inside infrastructure.
    """

    def __init__(self, knowledge_store: IKnowledgeStore) -> None:
        self._store = knowledge_store

    async def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Semantic search over the clinical knowledge base.

        Args:
            query:  Natural language search query.
            top_k:  Maximum number of results to return.

        Returns:
            List of dicts with keys: content, source, relevance.

        Raises:
            Exception: On any datastore error.
        """
        try:
            results = await self._store.search(query=query, top_k=top_k)
            logger.debug(f"KnowledgeService: search returned {len(results)} results for '{query}'")
            return results
        except Exception as e:
            logger.error(f"KnowledgeService.search failed for query '{query}': {e}")
            raise

    async def get_drug_interactions(
        self,
        medications: list[str],
    ) -> list[dict]:
        """
        Direct formulary lookup for known drug interactions.

        Args:
            medications: List of medication names to check.

        Returns:
            List of interaction records from the formulary.

        Raises:
            Exception: On any datastore error.
        """
        try:
            results = await self._store.get_drug_interactions(medications=medications)
            logger.debug(
                f"KnowledgeService: drug interaction check for "
                f"{medications} returned {len(results)} records"
            )
            return results
        except Exception as e:
            logger.error(f"KnowledgeService.get_drug_interactions failed: {e}")
            raise