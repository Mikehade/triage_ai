from __future__ import annotations
import json

from google.cloud import discoveryengine
from google.api_core.exceptions import GoogleAPIError

from src.infrastructure.knowledge.base import IKnowledgeStore
from utils.logger import get_logger

logger = get_logger()


class VertexKnowledgeStore(IKnowledgeStore):
    """
    Vertex AI Search (Discovery Engine) implementation of IKnowledgeStore.

    Backed by a Vertex AI Data Store loaded with:
    - Nigeria FMOH Standard Treatment Guidelines
    - WHO Malaria Treatment Guidelines (Nigeria context)
    - WHO TB treatment protocols
    - Nigeria National Drug Formulary
    - WHO Essential Medicines List

    For local development without a real datastore, swap in
    StaticKnowledgeStore via the DI container.
    """

    def __init__(
        self,
        project: str,
        location: str,
        datastore_id: str,
    ):
        self._project = project
        self._location = location
        self._datastore_id = datastore_id

        # Serving config path required by Discovery Engine API
        self._serving_config = (
            f"projects/{project}/locations/{location}"
            f"/collections/default_collection"
            f"/dataStores/{datastore_id}"
            f"/servingConfigs/default_config"
        )

        # Client is created once — uses GOOGLE_APPLICATION_CREDENTIALS
        self._search_client = discoveryengine.SearchServiceClient()
        self._recommend_client = None  # reserved for future use

    async def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Semantic search against the Vertex AI Data Store.

        Returns list of:
        {
            "content": str,
            "source": str,
            "relevance": float
        }
        """
        try:
            request = discoveryengine.SearchRequest(
                serving_config=self._serving_config,
                query=query,
                page_size=top_k,
                content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                    snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                        return_snippet=True,
                        max_snippet_count=1,
                    ),
                    summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                        summary_result_count=top_k,
                        include_citations=True,
                    ),
                ),
            )

            # Discovery Engine client is sync — run in executor to avoid
            # blocking the async event loop
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._search_client.search,
                request,
            )

            results = []
            for result in response.results:
                document = result.document

                # Extract snippet text
                content = ""
                if document.derived_struct_data:
                    snippets = document.derived_struct_data.get("snippets", [])
                    if snippets:
                        snippet = snippets[0]
                        content = snippet.get("snippet", "")

                # Fall back to document content if no snippet
                if not content and document.struct_data:
                    content = str(document.struct_data)

                # Source from document metadata
                source = "unknown"
                if document.struct_data:
                    source = (
                        document.struct_data.get("source", "")
                        or document.struct_data.get("title", "")
                        or document.name
                    )

                if content:
                    results.append({
                        "content": content,
                        "source": source,
                        "relevance": float(result.relevance_score)
                        if hasattr(result, "relevance_score")
                        else 1.0,
                    })

            logger.debug(
                f"VertexKnowledgeStore.search: "
                f"query='{query[:50]}' results={len(results)}"
            )
            return results

        except GoogleAPIError as e:
            logger.error(
                f"VertexKnowledgeStore.search failed: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"VertexKnowledgeStore.search unexpected error: {e}",
                exc_info=True,
            )
            raise

    async def get_drug_interactions(
        self,
        medications: list[str],
    ) -> list[dict]:
        """
        Formulary lookup for drug interactions.
        Searches the data store with a targeted drug interaction query.
        """
        if not medications:
            return []

        # Build a targeted query combining all drug names
        query = f"drug interactions contraindications: {', '.join(medications)}"

        try:
            results = await self.search(query=query, top_k=5)
            return results
        except Exception as e:
            logger.warning(
                f"VertexKnowledgeStore.get_drug_interactions failed: {e}. "
                "Returning empty — drug check will rely on LLM knowledge only."
            )
            return []